"""PC core: discover the phone, connect, receive audio.

Flow (matches the design):
  Phone  Mic Connecting..  -> sends "hello" about once a second to the PC discovery port
  PC     phone name shows  -> user clicks Connect -> PC sends "accept" to the phone
  Phone  Mic Online        -> sends audio packets to the PC audio port
Everything stays on the local network (UDP), nothing goes through the internet.
"""

import random
import socket
import threading
import time
from dataclasses import dataclass

from . import protocol as P
from .pcm import apply_gain, pcm_level


@dataclass
class Device:
    id: str
    name: str
    ip: str
    ctrl_port: int
    last_seen: float = 0.0


class PcCore:
    def __init__(self, discovery_port=P.DISCOVERY_PORT, audio_port=P.AUDIO_PORT,
                 bind_ip="0.0.0.0", device_ttl=3.5, audio_timeout=3.0):
        self._req_discovery_port = discovery_port
        self._req_audio_port = audio_port
        self._bind_ip = bind_ip
        self._device_ttl = device_ttl
        self._audio_timeout = audio_timeout

        # actual ports (filled in on start; useful when port 0 was requested)
        self.discovery_port = discovery_port
        self.audio_port = audio_port

        self.gain = 1.0
        self.on_audio = None   # callable(pcm: bytes) -> called on the audio thread
        self.on_state = None   # callable(event: str, device: Device)

        self._lock = threading.RLock()
        self._devices = {}
        self._active = None
        self._session = 0
        self._first = True
        self._connected_at = None   # monotonic time of the first audio packet (start of the connected timer)
        # Frozen timer: when a connection ends without the PC user clicking Disconnect
        # (audio timeout or the phone said bye) the connected time is kept here and shown
        # until the next Connect or a manual Disconnect.
        self._last_session_seconds = None
        self._last_session_reason = None   # "lost" (audio stopped) | "phone" (phone sent bye)
        self._next_seq = 0
        self._last_audio = 0.0
        self._level = 0.0
        self._stats = self._new_stats()

        self._running = False
        self._threads = []
        self._dsock = None
        self._asock = None

    # ---------- lifecycle ----------

    @staticmethod
    def _new_stats():
        return {"received": 0, "lost": 0, "late": 0, "rejected": 0, "bytes": 0}

    def _make_socket(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self._bind_ip, port))
        s.settimeout(0.25)
        return s

    def start(self):
        if self._running:
            return
        self._dsock = self._make_socket(self._req_discovery_port)
        try:
            self._asock = self._make_socket(self._req_audio_port)
        except OSError:
            self._dsock.close()
            raise
        self.discovery_port = self._dsock.getsockname()[1]
        self.audio_port = self._asock.getsockname()[1]
        self._running = True
        for target in (self._discovery_loop, self._audio_loop):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        if not self._running:
            return
        self.disconnect()
        self._running = False
        for t in self._threads:
            t.join(timeout=1.0)
        self._threads = []
        for s in (self._dsock, self._asock):
            try:
                s.close()
            except OSError:
                pass

    # ---------- API for the UI ----------

    def set_gain(self, gain):
        self.gain = max(0.0, min(4.0, float(gain)))

    def snapshot(self):
        now = time.monotonic()
        with self._lock:
            devices = [d for d in self._devices.values()
                       if d is self._active or now - d.last_seen <= self._device_ttl]
            active = self._active
            if active is not None:
                state = "connected"
            elif devices:
                state = "found"
            else:
                state = "waiting"
            level = self._level if (active and now - self._last_audio < 0.3) else 0.0
            since = self._connected_at
            frozen = None if active is not None else self._last_session_seconds
            return {
                "state": state,
                "devices": [{"id": d.id, "name": d.name, "ip": d.ip} for d in devices],
                "active": ({"id": active.id, "name": active.name, "ip": active.ip}
                           if active else None),
                "level": level,
                "connected_seconds": int(now - since) if (active and since is not None) else 0,
                # frozen connected time of the last connection that ended on its own (None = nothing to show)
                "last_session_seconds": frozen,
                "last_session_reason": self._last_session_reason if frozen is not None else None,
                "gain": self.gain,
                "stats": dict(self._stats),
            }

    def connect(self, device_id):
        with self._lock:
            dev = self._devices.get(device_id)
            if dev is None:
                return False
            if self._active is not None and self._active.id == device_id:
                return True
            if self._active is not None:
                self._send_bye(self._active)
            self._active = dev
            self._session = random.getrandbits(32) or 1
            self._first = True
            self._connected_at = None
            self._last_session_seconds = None
            self._last_session_reason = None
            self._stats = self._new_stats()
            self._last_audio = time.monotonic()
            self._level = 0.0
        self._send_accept(dev)
        self._notify("connected", dev)
        return True

    def disconnect(self):
        with self._lock:
            dev = self._active
            if dev is None:
                return
            self._send_bye(dev)
            self._clear_active()
            # the PC user ended it on purpose: nothing to keep frozen
            self._last_session_seconds = None
            self._last_session_reason = None
        self._notify("disconnected", dev)

    # ---------- internal ----------

    def _freeze_session(self, reason):
        """Keep how long the connection lasted (call with the lock held, before _clear_active).

        Only counts if audio actually arrived (the timer starts at the first audio packet).
        """
        if self._connected_at is None:
            self._last_session_seconds = None
            self._last_session_reason = None
            return
        # "lost": count until the last audio packet, so the silent seconds spent waiting for the
        # timeout are not included. "phone": the phone said bye, so up to now.
        end = self._last_audio if reason == "lost" else time.monotonic()
        self._last_session_seconds = max(0, int(end - self._connected_at))
        self._last_session_reason = reason

    def _clear_active(self):
        self._active = None
        self._session = 0
        self._level = 0.0
        self._connected_at = None

    def _notify(self, event, dev):
        cb = self.on_state
        if cb is not None:
            try:
                cb(event, dev)
            except Exception:
                pass

    def _send_accept(self, dev):
        msg = P.encode_msg(
            "accept", session=self._session, audio_port=self.audio_port,
            rate=P.SAMPLE_RATE, ch=P.CHANNELS, fmt="s16le", frame=P.FRAME_SAMPLES)
        try:
            self._dsock.sendto(msg, (dev.ip, dev.ctrl_port))
        except OSError:
            pass

    def _send_bye(self, dev):
        msg = P.encode_msg("bye", id="pc", session=self._session)
        try:
            self._dsock.sendto(msg, (dev.ip, dev.ctrl_port))
        except OSError:
            pass

    def _expire(self):
        now = time.monotonic()
        with self._lock:
            for dev_id in [i for i, d in self._devices.items()
                           if d is not self._active
                           and now - d.last_seen > self._device_ttl]:
                del self._devices[dev_id]

    def _discovery_loop(self):
        while self._running:
            try:
                data, addr = self._dsock.recvfrom(2048)
            except socket.timeout:
                self._expire()
                continue
            except OSError:
                if self._running:
                    time.sleep(0.05)
                    continue
                break
            msg = P.decode_msg(data)
            if msg is not None:
                kind = msg.get("t")
                if kind == "hello":
                    self._on_hello(msg, addr)
                elif kind == "bye":
                    self._on_phone_bye(msg)
            self._expire()

    def _on_hello(self, msg, addr):
        dev_id = str(msg.get("id", ""))[:64]
        if not dev_id:
            return
        name = str(msg.get("name", "HP"))[:48] or "HP"
        try:
            ctrl_port = int(msg.get("ctrl_port", P.PHONE_CTRL_PORT))
        except (TypeError, ValueError):
            ctrl_port = P.PHONE_CTRL_PORT
        if not 1 <= ctrl_port <= 65535:
            ctrl_port = P.PHONE_CTRL_PORT
        now = time.monotonic()
        resend = None
        with self._lock:
            dev = self._devices.get(dev_id)
            if dev is None:
                dev = Device(dev_id, name, addr[0], ctrl_port, now)
                self._devices[dev_id] = dev
            else:
                dev.name, dev.ip, dev.ctrl_port, dev.last_seen = name, addr[0], ctrl_port, now
            if self._active is not None and self._active.id == dev_id:
                # phone is still "Connecting.." (the earlier accept was lost) -> send it again
                self._active = dev
                resend = dev
        if resend is not None:
            self._send_accept(resend)

    def _on_phone_bye(self, msg):
        dev_id = str(msg.get("id", ""))
        ended = None
        with self._lock:
            if self._active is not None and self._active.id == dev_id:
                if msg.get("session") == self._session:
                    ended = self._active
                    self._freeze_session("phone")
                    self._clear_active()
                    self._devices.pop(dev_id, None)
            else:
                self._devices.pop(dev_id, None)  # phone cancelled before being connected
        if ended is not None:
            self._notify("disconnected", ended)

    def _audio_loop(self):
        while self._running:
            try:
                data, addr = self._asock.recvfrom(4096)
            except socket.timeout:
                self._check_audio_timeout()
                continue
            except OSError:
                if self._running:
                    time.sleep(0.05)
                    continue
                break
            self._handle_audio(data, addr)
            self._check_audio_timeout()

    def _handle_audio(self, data, addr):
        try:
            session, seq, pcm = P.unpack_audio(data)
        except P.ProtocolError:
            return
        if len(pcm) < 2:
            return
        with self._lock:
            act = self._active
            if act is None or session != self._session or addr[0] != act.ip:
                self._stats["rejected"] += 1
                return
            if self._first:
                self._first = False
                self._next_seq = seq
                self._connected_at = time.monotonic()
            ahead = (seq - self._next_seq) & 0xFFFFFFFF
            if ahead >= 0x80000000:
                self._stats["late"] += 1
                return
            self._stats["lost"] += ahead
            self._next_seq = (seq + 1) & 0xFFFFFFFF
            self._stats["received"] += 1
            self._stats["bytes"] += len(pcm)
            self._last_audio = time.monotonic()
            gain = self.gain
        pcm = apply_gain(pcm, gain)
        level = pcm_level(pcm)
        with self._lock:
            self._level = level
        cb = self.on_audio
        if cb is not None:
            cb(pcm)

    def _check_audio_timeout(self):
        lost = None
        with self._lock:
            if (self._active is not None
                    and time.monotonic() - self._last_audio > self._audio_timeout):
                lost = self._active
                self._send_bye(lost)
                self._freeze_session("lost")
                self._clear_active()
        if lost is not None:
            self._notify("lost", lost)
