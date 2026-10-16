import array
import unittest

from michp_pc import protocol as P
from michp_pc.audio_out import AudioOutput, JitterBuffer
from michp_pc.pcm import mono_to_stereo


class FakeStream:
    def __init__(self, **kw):
        self.kw = kw
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def stop(self):
        pass

    def close(self):
        self.closed = True


class FakeSD:
    class default:
        hostapi = 0
        device = (0, 0)  # default output = "Speakers"

    def __init__(self, devices):
        self._devices = devices
        self.streams = []

    def query_devices(self, device=None):
        return self._devices if device is None else self._devices[device]

    def RawOutputStream(self, **kw):
        s = FakeStream(**kw)
        self.streams.append(s)
        return s


DEVICES = [
    {"name": "Speakers", "max_output_channels": 2, "hostapi": 0},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_output_channels": 2, "hostapi": 0},
    {"name": "Microphone", "max_output_channels": 0, "hostapi": 0},
    {"name": "Speakers (WASAPI)", "max_output_channels": 2, "hostapi": 1},
]


def mono_frame(value):
    return array.array("h", [value] * P.FRAME_SAMPLES).tobytes()


class JitterBufferTests(unittest.TestCase):
    def test_silence_until_prebuffer(self):
        jb = JitterBuffer(prebuffer_ms=60)
        jb.push(mono_to_stereo(mono_frame(5)))  # only 20 ms so far
        self.assertEqual(jb.pop(3840), bytes(3840))
        self.assertEqual(jb.underruns, 0)

    def test_plays_in_order_after_prebuffer(self):
        jb = JitterBuffer(prebuffer_ms=60)
        for v in (1, 2, 3, 4):
            jb.push(mono_to_stereo(mono_frame(v)))
        for v in (1, 2, 3, 4):
            out = array.array("h")
            out.frombytes(jb.pop(3840))
            self.assertEqual(set(out), {v})

    def test_underrun_pads_with_silence_and_rebuffers(self):
        jb = JitterBuffer(prebuffer_ms=40)
        for v in (7, 7):
            jb.push(mono_to_stereo(mono_frame(v)))
        jb.pop(3840)
        out = jb.pop(3840 * 2)          # ask for more than there is
        self.assertEqual(len(out), 3840 * 2)
        self.assertEqual(jb.underruns, 1)
        self.assertEqual(jb.pop(3840), bytes(3840))  # waiting to fill up again

    def test_overflow_drops_oldest_and_stays_aligned(self):
        jb = JitterBuffer(prebuffer_ms=20, max_ms=100)
        for v in range(1, 21):          # 20 frame = 400 ms, max 100 ms
            jb.push(mono_to_stereo(mono_frame(v)))
        self.assertLessEqual(jb.buffered_bytes, int(P.SAMPLE_RATE * 0.1) * 4)
        self.assertEqual(jb.buffered_bytes % 4, 0)
        self.assertGreater(jb.overflows, 0)
        out = array.array("h")
        out.frombytes(jb.pop(3840))
        self.assertGreater(out[0], 10)  # the old data has been dropped


class AudioOutputTests(unittest.TestCase):
    def test_finds_cable_input_and_filters_host_api(self):
        sd = FakeSD(DEVICES)
        ao = AudioOutput(sd=sd)
        names = [d["name"] for d in ao.list_devices(max_age=0)]
        self.assertEqual(names, ["Speakers", "CABLE Input (VB-Audio Virtual Cable)"])
        self.assertEqual(ao.auto_virtual_index(), 1)
        ao.start()
        self.assertEqual(len(sd.streams), 1)
        self.assertEqual(sd.streams[0].kw["device"], 1)
        self.assertEqual(sd.streams[0].kw["channels"], 2)
        self.assertTrue(sd.streams[0].started)
        self.assertEqual(ao.info()["virtual_name"], "CABLE Input (VB-Audio Virtual Cable)")

    def test_no_cable_means_no_virtual_stream(self):
        sd = FakeSD(DEVICES[:1])
        ao = AudioOutput(sd=sd)
        ao.start()
        self.assertEqual(sd.streams, [])
        self.assertIsNone(ao.info()["virtual_index"])

    def test_audio_reaches_stream_callback_as_stereo(self):
        sd = FakeSD(DEVICES)
        ao = AudioOutput(sd=sd)
        ao.start()
        cb = ao._virtual_stream.kw["callback"] if hasattr(ao._virtual_stream, "kw") else None
        for _ in range(4):
            ao.push(mono_frame(1000))
        outdata = bytearray(P.FRAME_SAMPLES * 4)
        cb(outdata, P.FRAME_SAMPLES, None, None)
        out = array.array("h")
        out.frombytes(bytes(outdata))
        self.assertEqual(set(out), {1000})

    def test_monitor_toggle_opens_default_device(self):
        sd = FakeSD(DEVICES)
        ao = AudioOutput(sd=sd)
        ao.start()
        self.assertTrue(ao.set_monitor(True))
        self.assertEqual(len(sd.streams), 2)
        self.assertIsNone(sd.streams[1].kw["device"])
        self.assertTrue(ao.info()["monitor"])
        self.assertFalse(ao.set_monitor(False))
        self.assertTrue(sd.streams[1].closed)
        self.assertFalse(ao.info()["monitor"])

    def test_monitor_not_doubled_when_output_is_speakers(self):
        # user picks Speakers in the Output box: monitor must not open a second stream
        sd = FakeSD(DEVICES)
        ao = AudioOutput(sd=sd)
        ao.start()
        ao.select_virtual(0)
        n = len(sd.streams)
        self.assertTrue(ao.set_monitor(True))
        self.assertEqual(len(sd.streams), n)
        info = ao.info()
        self.assertTrue(info["monitor"])
        self.assertTrue(info["monitor_shared"])
        self.assertFalse(info["virtual_is_cable"])
        self.assertFalse(ao.set_monitor(False))
        self.assertFalse(sd.streams[-1].closed)  # the virtual mic stream must not die with it

    def test_info_reports_cable_and_monitor_target(self):
        ao = AudioOutput(sd=FakeSD(DEVICES))
        ao.start()
        info = ao.info()
        self.assertTrue(info["virtual_is_cable"])
        self.assertFalse(info["monitor_shared"])
        self.assertEqual(info["monitor_target"], "Speakers")

    def test_open_failure_is_reported_not_raised(self):
        class BrokenSD(FakeSD):
            def RawOutputStream(self, **kw):
                raise OSError("device sibuk")

        ao = AudioOutput(sd=BrokenSD(DEVICES))
        self.assertFalse(ao.set_monitor(True))
        self.assertIn("device sibuk", ao.info()["error"])

    def test_push_without_streams_is_noop(self):
        ao = AudioOutput(sd=FakeSD([]))  # no devices at all
        ao.push(mono_frame(1))  # must not fail even without a stream
        self.assertEqual(ao.info()["devices"], [])


if __name__ == "__main__":
    unittest.main()
