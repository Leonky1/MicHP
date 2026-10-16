"""Audio output: sends the phone's sound to the virtual mic (VB-Cable) and to headphones (hear yourself).

How the virtual mic works on Windows:
  this software -> plays to "CABLE Input" -> other apps (Discord, OBS, Zoom)
  pick "CABLE Output" as their microphone.
"""

import threading
import time

from . import protocol as P
from .pcm import mono_to_stereo

STEREO_FRAME_BYTES = 4  # 2 channel x 16-bit


class JitterBuffer:
    """Small byte queue: holds a little audio before playing so it does not stutter."""

    def __init__(self, prebuffer_ms=60, max_ms=240, rate=P.SAMPLE_RATE,
                 frame_bytes=STEREO_FRAME_BYTES):
        self._frame_bytes = frame_bytes
        self._pre = int(rate * prebuffer_ms / 1000) * frame_bytes
        self._max = int(rate * max_ms / 1000) * frame_bytes
        self._buf = bytearray()
        self._primed = False
        self._lock = threading.Lock()
        self.underruns = 0
        self.overflows = 0

    def push(self, data):
        with self._lock:
            self._buf += data
            if len(self._buf) > self._max:
                drop = len(self._buf) - self._max
                drop -= drop % self._frame_bytes
                del self._buf[:drop]
                self.overflows += 1

    def pop(self, n):
        """Always returns exactly n bytes (padded with silence if there is not enough data)."""
        with self._lock:
            if not self._primed:
                if len(self._buf) >= self._pre:
                    self._primed = True
                else:
                    return bytes(n)
            if len(self._buf) >= n:
                out = bytes(self._buf[:n])
                del self._buf[:n]
                return out
            out = bytes(self._buf)
            self._buf.clear()
            self._primed = False
            self.underruns += 1
            return out + bytes(n - len(out))

    def clear(self):
        with self._lock:
            self._buf.clear()
            self._primed = False

    @property
    def buffered_bytes(self):
        with self._lock:
            return len(self._buf)


class AudioOutput:
    def __init__(self, sd=None):
        self.error = None
        self.last_error = None
        self._sd = sd
        if self._sd is None:
            try:
                import sounddevice
                self._sd = sounddevice
            except Exception:
                self._sd = None
                self.error = "sounddevice is not installed (run install.bat)"
        self._lock = threading.RLock()
        self._virtual = JitterBuffer()
        self._monitor = JitterBuffer()
        self._virtual_stream = None
        self._monitor_stream = None
        self._virtual_index = None
        self._monitor_on = False
        self._dev_cache = ([], 0.0)

    @property
    def available(self):
        return self._sd is not None

    # ---------- device list ----------

    def list_devices(self, max_age=3.0):
        if not self.available:
            return []
        devices, stamp = self._dev_cache
        if devices and time.monotonic() - stamp < max_age:
            return devices
        out = []
        try:
            host = self._sd.default.hostapi
        except Exception:
            host = None
        try:
            for i, d in enumerate(self._sd.query_devices()):
                if d.get("max_output_channels", 0) <= 0:
                    continue
                if host is not None and d.get("hostapi") != host:
                    continue
                out.append({"index": i, "name": d["name"]})
        except Exception as e:
            self.last_error = "Could not read the audio device list: %s" % e
            return []
        self._dev_cache = (out, time.monotonic())
        return out

    def default_output(self):
        """(index, name) of the Windows default output, or (None, None)."""
        if not self.available:
            return None, None
        try:
            idx = self._sd.default.device[1]
            if idx is None or idx < 0:
                return None, None
            return int(idx), self._sd.query_devices(int(idx))["name"]
        except Exception:
            return None, None

    @staticmethod
    def is_cable(name):
        return bool(name) and "cable" in name.lower()

    def auto_virtual_index(self):
        for d in self.list_devices(max_age=0):
            if "cable input" in d["name"].lower():
                return d["index"]
        return None

    # ---------- stream ----------

    def _open(self, index, buf):
        def callback(outdata, frames, time_info, status):
            outdata[:] = buf.pop(frames * STEREO_FRAME_BYTES)

        try:
            stream = self._sd.RawOutputStream(
                samplerate=P.SAMPLE_RATE, channels=2, dtype="int16",
                device=index, blocksize=P.FRAME_SAMPLES, callback=callback)
            stream.start()
            self.last_error = None
            return stream
        except Exception as e:
            self.last_error = "Could not open the audio output: %s" % e
            return None

    @staticmethod
    def _close(stream):
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    def start(self):
        if self.available:
            self.select_virtual(self.auto_virtual_index())

    def stop(self):
        with self._lock:
            self._close(self._virtual_stream)
            self._close(self._monitor_stream)
            self._virtual_stream = self._monitor_stream = None
            self._virtual_index = None
            self._monitor_on = False

    def select_virtual(self, index):
        """Choose the output device for the virtual mic (None = turn off)."""
        with self._lock:
            self._close(self._virtual_stream)
            self._virtual_stream = None
            self._virtual_index = None
            self._virtual.clear()
            if index is None or not self.available:
                return True
            stream = self._open(index, self._virtual)
            if stream is None:
                return False
            self._virtual_stream = stream
            self._virtual_index = index
            return True

    def _monitor_shares_virtual(self):
        """True if the virtual mic output is the same as the default output (speakers).

        That happens when the user picks the speakers in the Output box. Opening a second
        stream to the same device would double the sound, so the stream is shared instead.
        """
        d_idx, _ = self.default_output()
        return (self._virtual_stream is not None and self._virtual_index is not None
                and d_idx is not None and d_idx == self._virtual_index)

    def set_monitor(self, on):
        """Hear yourself through the default output (headphones/speakers)."""
        with self._lock:
            if on and not self.available:
                return False
            if on:
                if self._monitor_stream is None and not self._monitor_shares_virtual():
                    self._monitor.clear()
                    stream = self._open(None, self._monitor)
                    if stream is None:
                        self._monitor_on = False
                        return False
                    self._monitor_stream = stream
                self._monitor_on = True
            else:
                if self._monitor_stream is not None:
                    self._close(self._monitor_stream)
                    self._monitor_stream = None
                    self._monitor.clear()
                self._monitor_on = False
            return self._monitor_on

    # ---------- data ----------

    def push(self, pcm_mono):
        """Called for every audio frame from the phone (core audio thread)."""
        v = self._virtual_stream is not None
        m = self._monitor_stream is not None
        if not (v or m):
            return
        stereo = mono_to_stereo(pcm_mono)
        if v:
            self._virtual.push(stereo)
        if m:
            self._monitor.push(stereo)

    def info(self):
        devices = self.list_devices()
        name = None
        for d in devices:
            if d["index"] == self._virtual_index:
                name = d["name"]
        _, default_name = self.default_output()
        return {
            "available": self.available,
            "monitor_target": default_name,
            "virtual_is_cable": self.is_cable(name) if name else None,
            "monitor_shared": self._monitor_shares_virtual(),
            "error": self.error or self.last_error,
            "monitor": self._monitor_on,
            "virtual_index": self._virtual_index,
            "virtual_name": name,
            "devices": devices,
            "underruns": self._virtual.underruns,
        }
