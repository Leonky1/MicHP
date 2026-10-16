"""Fake phone for testing: pretends to be the phone app and sends a sine tone to the PC.

Example (PC running on the same machine):
    python -m michp_pc.fake_phone --seconds 5
Example (fake phone on another PC on the same WiFi, using broadcast):
    python -m michp_pc.fake_phone --host 255.255.255.255
"""

import argparse
import math
import socket
import struct
import threading
import time
import uuid

from . import protocol as P


def run_fake_phone(pc_host="127.0.0.1", discovery_port=P.DISCOVERY_PORT,
                   name="Fake HP", ctrl_port=0, seconds=5.0, freq=440.0,
                   amp=0.5, stop_event=None, log=None, device_id=None,
                   hello_interval=0.5, send_bye=True, connect_timeout=30.0):
    """Run one fake-phone session. Returns a result dict."""
    log = log or (lambda *a: None)
    stop_event = stop_event or threading.Event()
    device_id = device_id or "fake-" + uuid.uuid4().hex[:8]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", ctrl_port))
    sock.settimeout(0.05)
    my_ctrl_port = sock.getsockname()[1]
    result = {"connected": False, "frames_sent": 0, "session": None, "pc_bye": False}

    hello = P.encode_msg("hello", id=device_id, name=name, ctrl_port=my_ctrl_port)
    deadline = time.monotonic() + connect_timeout
    last_hello = 0.0
    accept = None
    log("Mic Connecting.. (sending hello)")
    while not stop_event.is_set() and accept is None and time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_hello >= hello_interval:
            sock.sendto(hello, (pc_host, discovery_port))
            last_hello = now
        try:
            data, addr = sock.recvfrom(2048)
        except (socket.timeout, ConnectionResetError):
            continue
        msg = P.decode_msg(data)
        if msg and msg.get("t") == "accept":
            accept = (msg, addr)
    if accept is None:
        sock.close()
        return result

    msg, addr = accept
    pc_ip = addr[0]
    audio_port = int(msg["audio_port"])
    session = int(msg["session"])
    result.update(connected=True, session=session)
    log("Mic Online -> sending audio to %s:%d" % (pc_ip, audio_port))

    sock.setblocking(False)
    step = 2.0 * math.pi * freq / P.SAMPLE_RATE
    phase = 0.0
    seq = 0
    t0 = time.monotonic()
    end = t0 + seconds
    while not stop_event.is_set():
        now = time.monotonic()
        if now >= end:
            break
        target = t0 + seq * 0.02
        if target > now:
            time.sleep(min(target - now, 0.01))
            continue
        samples = []
        for _ in range(P.FRAME_SAMPLES):
            samples.append(int(amp * 32767 * math.sin(phase)))
            phase += step
        phase %= 2.0 * math.pi
        pcm = struct.pack("<%dh" % len(samples), *samples)
        sock.sendto(P.pack_audio(session, seq, pcm), (pc_ip, audio_port))
        seq += 1
        result["frames_sent"] += 1
        try:
            data, _ = sock.recvfrom(2048)
        except (BlockingIOError, ConnectionResetError):
            continue
        m = P.decode_msg(data)
        if m and m.get("t") == "bye":
            result["pc_bye"] = True
            break

    if send_bye:
        sock.sendto(P.encode_msg("bye", id=device_id, session=session),
                    (pc_ip, discovery_port))
    sock.close()
    log("done, %d frames sent" % result["frames_sent"])
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fake phone for testing MicHP")
    ap.add_argument("--host", default="127.0.0.1",
                    help="PC IP, or 255.255.255.255 for broadcast")
    ap.add_argument("--port", type=int, default=P.DISCOVERY_PORT)
    ap.add_argument("--name", default="Fake HP")
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--freq", type=float, default=440.0)
    ap.add_argument("--amp", type=float, default=0.5)
    args = ap.parse_args(argv)
    try:
        run_fake_phone(args.host, args.port, args.name, P.PHONE_CTRL_PORT,
                       args.seconds, args.freq, args.amp, log=print)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
