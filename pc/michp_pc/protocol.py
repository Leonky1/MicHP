"""MicHP protocol v1. Full description in PROTOCOL.md."""

import json
import struct

VERSION = 1

DISCOVERY_PORT = 48100   # PC listens: hello / bye from the phone
AUDIO_PORT = 48101       # PC listens: audio packets from the phone
PHONE_CTRL_PORT = 48102  # Phone listens: accept / bye from the PC

SAMPLE_RATE = 48000
CHANNELS = 1
BYTES_PER_SAMPLE = 2                      # PCM signed 16-bit little-endian
FRAME_SAMPLES = 960                       # 20 ms @ 48 kHz
FRAME_BYTES = FRAME_SAMPLES * CHANNELS * BYTES_PER_SAMPLE  # 1920

MAGIC = b"WM"
TYPE_AUDIO = 1
_HEADER = struct.Struct("<2sBBII")        # magic, version, type, session, seq
HEADER_SIZE = _HEADER.size                # 12 byte


class ProtocolError(ValueError):
    """Invalid packet."""


def pack_audio(session, seq, pcm):
    header = _HEADER.pack(MAGIC, VERSION, TYPE_AUDIO,
                          session & 0xFFFFFFFF, seq & 0xFFFFFFFF)
    return header + pcm


def unpack_audio(data):
    """Return (session, seq, pcm_bytes) or raise ProtocolError."""
    if len(data) < HEADER_SIZE:
        raise ProtocolError("packet too short")
    magic, ver, typ, session, seq = _HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ProtocolError("bad magic")
    if ver != VERSION:
        raise ProtocolError("unsupported version")
    if typ != TYPE_AUDIO:
        raise ProtocolError("not an audio packet")
    return session, seq, data[HEADER_SIZE:]


def encode_msg(msg_type, **fields):
    """Control message = a small JSON over UDP."""
    msg = {"t": msg_type, "v": VERSION}
    msg.update(fields)
    return json.dumps(msg, separators=(",", ":")).encode("utf-8")


def decode_msg(data):
    """Return the message dict, or None if it is not a valid control message."""
    try:
        msg = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(msg, dict):
        return None
    if msg.get("v") != VERSION or not isinstance(msg.get("t"), str):
        return None
    return msg
