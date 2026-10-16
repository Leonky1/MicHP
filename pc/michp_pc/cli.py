"""Terminal version of the PC software (for testing without the UI)."""

import argparse
import sys
import time
import wave

from . import protocol as P
from .core import PcCore


def level_bar(level, width=32):
    n = int(round(level * width))
    return "#" * n + "-" * (width - n)


def _pick_device(core, auto):
    while True:
        devices = core.snapshot()["devices"]
        if not devices:
            sys.stdout.write("\rWaiting for a phone.. open MicHP on the phone and tap Mic Offline   ")
            sys.stdout.flush()
            time.sleep(0.5)
            continue
        if auto:
            return devices[0]
        print("\nPhones found:")
        for i, d in enumerate(devices, 1):
            print("  %d. %s (%s)" % (i, d["name"], d["ip"]))
        raw = input("Connect to which number? (Enter = refresh, q = quit) ").strip().lower()
        if raw == "q":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(devices):
            return devices[int(raw) - 1]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="michp_pc", description="MicHP - PC side (terminal)")
    ap.add_argument("--auto", action="store_true", help="connect to the first phone right away")
    ap.add_argument("--record", help="save the received audio to a WAV file")
    ap.add_argument("--gain", type=float, default=1.0, help="volume multiplier (1.0 = normal)")
    ap.add_argument("--discovery-port", type=int, default=P.DISCOVERY_PORT)
    ap.add_argument("--audio-port", type=int, default=P.AUDIO_PORT)
    args = ap.parse_args(argv)

    core = PcCore(discovery_port=args.discovery_port, audio_port=args.audio_port)
    core.set_gain(args.gain)

    wav = None
    if args.record:
        wav = wave.open(args.record, "wb")
        wav.setnchannels(P.CHANNELS)
        wav.setsampwidth(P.BYTES_PER_SAMPLE)
        wav.setframerate(P.SAMPLE_RATE)
        core.on_audio = wav.writeframes

    try:
        core.start()
    except OSError as e:
        print("Could not open UDP ports %d/%d: %s" % (args.discovery_port, args.audio_port, e))
        print("This software may already be running in another window.")
        if wav:
            wav.close()
        return 1

    print("Listening on UDP %d (discovery) and %d (audio). Press Ctrl+C to quit."
          % (core.discovery_port, core.audio_port))
    try:
        device = _pick_device(core, args.auto)
        if device is None:
            return 0
        if not core.connect(device["id"]):
            print("The phone has disappeared from the network, try again.")
            return 1
        print("Connected to %s" % device["name"])
        while True:
            snap = core.snapshot()
            if snap["state"] != "connected":
                frozen = snap["last_session_seconds"]
                if frozen is None:
                    print("\nConnection ended.")
                else:
                    print("\nConnection ended after %02d:%02d:%02d."
                          % (frozen // 3600, frozen // 60 % 60, frozen % 60))
                break
            st = snap["stats"]
            sys.stdout.write("\r[%s] %3d%%  packets=%d lost=%d "
                             % (level_bar(snap["level"]), int(snap["level"] * 100),
                                st["received"], st["lost"]))
            sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
    finally:
        core.disconnect()
        core.stop()
        if wav:
            wav.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
