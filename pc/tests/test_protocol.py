import array
import math
import unittest

from michp_pc import protocol as P
from michp_pc.pcm import apply_gain, mono_to_stereo, pcm_level


def sine(amp, n=960, freq=440.0):
    s = [int(amp * 32767 * math.sin(2 * math.pi * freq * i / P.SAMPLE_RATE)) for i in range(n)]
    return array.array("h", s).tobytes()


class ProtocolTests(unittest.TestCase):
    def test_audio_roundtrip(self):
        pcm = sine(0.5)
        pkt = P.pack_audio(123456, 7, pcm)
        self.assertEqual(len(pkt), P.HEADER_SIZE + len(pcm))
        self.assertEqual(P.unpack_audio(pkt), (123456, 7, pcm))

    def test_seq_wraps_to_u32(self):
        pkt = P.pack_audio(1, 0x1_0000_0005, b"\x00\x00")
        self.assertEqual(P.unpack_audio(pkt)[1], 5)

    def test_bad_packets_raise(self):
        with self.assertRaises(P.ProtocolError):
            P.unpack_audio(b"abc")
        with self.assertRaises(P.ProtocolError):
            P.unpack_audio(b"XX" + b"\x00" * 20)
        bad_version = bytearray(P.pack_audio(1, 1, b"\x00\x00"))
        bad_version[2] = 99
        with self.assertRaises(P.ProtocolError):
            P.unpack_audio(bytes(bad_version))

    def test_control_messages(self):
        raw = P.encode_msg("hello", id="abc", name="HP Ferdi", ctrl_port=48102)
        msg = P.decode_msg(raw)
        self.assertEqual(msg["t"], "hello")
        self.assertEqual(msg["name"], "HP Ferdi")
        self.assertIsNone(P.decode_msg(b"\xff\xfe"))
        self.assertIsNone(P.decode_msg(b"[1,2,3]"))
        self.assertIsNone(P.decode_msg(b'{"t":"hello","v":99}'))
        self.assertIsNone(P.decode_msg(P.pack_audio(1, 1, b"\x00\x00")))


class PcmTests(unittest.TestCase):
    def test_level_silence_and_loud(self):
        self.assertEqual(pcm_level(b""), 0.0)
        self.assertEqual(pcm_level(bytes(1920)), 0.0)
        self.assertGreater(pcm_level(sine(0.9)), 0.9)
        self.assertLess(pcm_level(sine(0.001)), 0.2)

    def test_level_is_monotonic(self):
        self.assertLess(pcm_level(sine(0.05)), pcm_level(sine(0.2)))
        self.assertLess(pcm_level(sine(0.2)), pcm_level(sine(0.8)))

    def test_gain_scales_and_clips(self):
        pcm = sine(0.25)
        doubled = array.array("h")
        doubled.frombytes(apply_gain(pcm, 2.0))
        orig = array.array("h")
        orig.frombytes(pcm)
        self.assertAlmostEqual(max(doubled) / max(orig), 2.0, delta=0.05)
        clipped = array.array("h")
        clipped.frombytes(apply_gain(sine(0.9), 4.0))
        self.assertEqual(max(clipped), 32767)
        self.assertEqual(min(clipped), -32768)
        self.assertIs(apply_gain(pcm, 1.0), pcm)
        self.assertEqual(apply_gain(pcm, 0.0), bytes(len(pcm)))

    def test_mono_to_stereo(self):
        mono = array.array("h", [1, -2, 3]).tobytes()
        stereo = array.array("h")
        stereo.frombytes(mono_to_stereo(mono))
        self.assertEqual(list(stereo), [1, 1, -2, -2, 3, 3])


if __name__ == "__main__":
    unittest.main()
