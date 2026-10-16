"""16-bit mono PCM helpers. Pure Python (audioop was removed in Python 3.13)."""

import array
import math
import sys


def _samples(pcm):
    a = array.array("h")
    a.frombytes(pcm[: len(pcm) - (len(pcm) % 2)])
    if sys.byteorder == "big":
        a.byteswap()
    return a


def _to_bytes(a):
    if sys.byteorder == "big":
        a.byteswap()
    return a.tobytes()


def pcm_level(pcm, floor_db=-60.0):
    """Sound level 0.0..1.0 from RMS (dBFS scale, -60 dB = 0, 0 dB = 1)."""
    a = _samples(pcm)
    if not a:
        return 0.0
    acc = 0
    for s in a:
        acc += s * s
    rms = math.sqrt(acc / len(a))
    if rms <= 0:
        return 0.0
    db = 20.0 * math.log10(rms / 32768.0)
    return max(0.0, min(1.0, (db - floor_db) / (-floor_db)))


def apply_gain(pcm, gain):
    """Multiply the amplitude by gain, hard clip at the 16-bit limits."""
    if gain == 1.0:
        return pcm
    a = _samples(pcm)
    out = array.array(
        "h", (max(-32768, min(32767, int(s * gain))) for s in a)
    )
    return _to_bytes(out)


def mono_to_stereo(pcm):
    """Duplicate mono into stereo (L = R). Used for 2-channel output devices."""
    a = _samples(pcm)
    out = array.array("h", bytes(len(a) * 4))
    out[0::2] = a
    out[1::2] = a
    return _to_bytes(out)
