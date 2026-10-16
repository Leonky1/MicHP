"""End-to-end tests on loopback: PcCore <-> fake phone (real UDP)."""

import array
import socket
import threading
import time
import unittest

from michp_pc import protocol as P
from michp_pc.core import PcCore
from michp_pc.fake_phone import run_fake_phone


def wait_for(cond, timeout=3.0, step=0.02):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(step)
    return False


class IntegrationBase(unittest.TestCase):
    def setUp(self):
        self.core = PcCore(discovery_port=0, audio_port=0, bind_ip="127.0.0.1",
                           audio_timeout=0.8)
        self.core.start()
        self.frames = []
        self.core.on_audio = self.frames.append
        self.result = {}
        self.threads = []

    def tearDown(self):
        self.core.stop()
        for t in self.threads:
            t.join(timeout=2)

    def start_phone(self, **kw):
        kw.setdefault("pc_host", "127.0.0.1")
        kw["discovery_port"] = self.core.discovery_port
        t = threading.Thread(
            target=lambda: self.result.update(run_fake_phone(**kw)), daemon=True)
        t.start()
        self.threads.append(t)
        return t

    def connect_first(self):
        self.assertTrue(wait_for(lambda: self.core.snapshot()["devices"]))
        dev = self.core.snapshot()["devices"][0]
        self.assertTrue(self.core.connect(dev["id"]))
        return dev


class ConnectedTimeTests(IntegrationBase):
    def test_zero_until_audio_then_counts_and_resets(self):
        self.assertEqual(self.core.snapshot()["connected_seconds"], 0)
        t = self.start_phone(seconds=1.0, amp=0.3)
        self.connect_first()
        self.assertTrue(wait_for(lambda: self.core._connected_at is not None))
        s = self.core.snapshot()["connected_seconds"]
        self.assertIsInstance(s, int)
        self.assertLessEqual(s, 1)
        # move the timer start back 1 h 2 min 5 s -> must read 3725
        with self.core._lock:
            self.core._connected_at -= 3725
        self.assertIn(self.core.snapshot()["connected_seconds"], (3725, 3726))
        t.join(timeout=3)
        self.assertTrue(wait_for(lambda: self.core.snapshot()["state"] != "connected", timeout=3.0))
        self.assertEqual(self.core.snapshot()["connected_seconds"], 0)


class FrozenTimeTests(IntegrationBase):
    """When a connection ends on its own, the connected time is frozen and kept on screen."""

    def shift_timer(self, seconds):
        self.assertTrue(wait_for(lambda: self.core._connected_at is not None))
        with self.core._lock:
            self.core._connected_at -= seconds

    def test_nothing_frozen_before_any_connection(self):
        s = self.core.snapshot()
        self.assertIsNone(s["last_session_seconds"])
        self.assertIsNone(s["last_session_reason"])

    def test_audio_lost_freezes_connected_time(self):
        self.start_phone(seconds=0.3, send_bye=False)   # phone just goes silent
        self.connect_first()
        self.shift_timer(3725)
        self.assertTrue(wait_for(lambda: self.core.snapshot()["state"] != "connected", timeout=3.0))
        s = self.core.snapshot()
        self.assertEqual(s["last_session_reason"], "lost")
        # audio ran ~0.3 s; the 0.8 s spent waiting for the timeout must NOT be counted
        self.assertTrue(3725 <= s["last_session_seconds"] <= 3726, s["last_session_seconds"])
        self.assertEqual(s["connected_seconds"], 0)
        # frozen: the value does not keep growing
        frozen = s["last_session_seconds"]
        time.sleep(1.3)
        self.assertEqual(self.core.snapshot()["last_session_seconds"], frozen)

    def test_phone_bye_freezes_connected_time(self):
        self.start_phone(seconds=0.5)                   # sends bye at the end
        self.connect_first()
        self.shift_timer(100)
        self.assertTrue(wait_for(lambda: self.core.snapshot()["state"] != "connected", timeout=3.0))
        s = self.core.snapshot()
        self.assertEqual(s["last_session_reason"], "phone")
        self.assertTrue(100 <= s["last_session_seconds"] <= 103)

    def test_manual_disconnect_does_not_freeze(self):
        self.start_phone(seconds=5.0)
        self.connect_first()
        self.assertTrue(wait_for(lambda: len(self.frames) > 5))
        self.core.disconnect()
        s = self.core.snapshot()
        self.assertIsNone(s["last_session_seconds"])
        self.assertIsNone(s["last_session_reason"])

    def test_dropped_before_any_audio_has_nothing_to_freeze(self):
        # connected but no audio ever arrived -> the timer never started -> nothing to record
        self.start_phone(seconds=0.0, send_bye=False)
        dev = self.connect_first()
        self.assertTrue(wait_for(lambda: self.core.snapshot()["state"] != "connected", timeout=3.0))
        self.assertIsNone(self.core.snapshot()["last_session_seconds"])

    def test_new_connection_clears_frozen_time(self):
        self.start_phone(seconds=0.3, send_bye=False)
        dev = self.connect_first()
        self.shift_timer(50)
        self.assertTrue(wait_for(lambda: self.core.snapshot()["state"] != "connected", timeout=3.0))
        self.assertIsNotNone(self.core.snapshot()["last_session_seconds"])
        self.assertTrue(self.core.connect(dev["id"]))   # connect again
        s = self.core.snapshot()
        self.assertIsNone(s["last_session_seconds"])
        self.assertEqual(s["state"], "connected")


class StreamTests(IntegrationBase):
    def test_discover_connect_stream_then_bye(self):
        t = self.start_phone(seconds=1.0, amp=0.5)
        dev = self.connect_first()
        self.assertEqual(dev["name"], "Fake HP")

        peak = 0.0
        while t.is_alive():
            peak = max(peak, self.core.snapshot()["level"])
            time.sleep(0.02)
        t.join(3)

        self.assertGreaterEqual(len(self.frames), 40)
        self.assertTrue(all(len(f) == P.FRAME_BYTES for f in self.frames))
        self.assertLessEqual(self.core.snapshot()["stats"]["lost"], 2)
        self.assertGreater(peak, 0.7)
        # phone sends bye -> PC goes back to "waiting"
        self.assertTrue(wait_for(lambda: self.core.snapshot()["state"] == "waiting"))

    def test_gain_is_applied(self):
        self.core.set_gain(2.0)
        t = self.start_phone(seconds=0.5, amp=0.25)
        self.connect_first()
        t.join(3)
        self.assertGreater(len(self.frames), 10)
        a = array.array("h")
        a.frombytes(b"".join(self.frames))
        self.assertGreater(max(a), 15000)
        self.assertLess(max(a), 17500)

    def test_disconnect_from_pc_stops_phone(self):
        t = self.start_phone(seconds=5.0)
        self.connect_first()
        self.assertTrue(wait_for(lambda: len(self.frames) > 5))
        self.core.disconnect()
        t.join(3)
        self.assertFalse(t.is_alive())
        self.assertTrue(self.result.get("pc_bye"))
        self.assertLess(self.result["frames_sent"], 200)

    def test_audio_timeout_without_bye(self):
        self.start_phone(seconds=0.3, send_bye=False)
        self.connect_first()
        self.assertTrue(wait_for(lambda: len(self.frames) > 3))
        self.assertTrue(wait_for(
            lambda: self.core.snapshot()["state"] != "connected", timeout=3.0))


class RawPacketTests(IntegrationBase):
    """A 'manual' phone over raw sockets to test edge cases."""

    def setUp(self):
        super().setUp()
        self.ctrl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ctrl.bind(("127.0.0.1", 0))
        self.ctrl.settimeout(2.0)
        self.audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hello = P.encode_msg("hello", id="raw-1", name="Raw HP",
                             ctrl_port=self.ctrl.getsockname()[1])
        self.ctrl.sendto(hello, ("127.0.0.1", self.core.discovery_port))
        self.assertTrue(wait_for(lambda: self.core.snapshot()["devices"]))
        self.assertTrue(self.core.connect("raw-1"))
        accept = P.decode_msg(self.ctrl.recvfrom(2048)[0])
        self.assertEqual(accept["t"], "accept")
        self.session = accept["session"]
        self.dest = ("127.0.0.1", accept["audio_port"])

    def tearDown(self):
        self.ctrl.close()
        self.audio.close()
        super().tearDown()

    def send(self, session, seq):
        self.audio.sendto(P.pack_audio(session, seq, bytes(P.FRAME_BYTES)), self.dest)

    def stats(self):
        return self.core.snapshot()["stats"]

    def test_wrong_session_rejected(self):
        self.send(self.session + 1, 0)
        self.assertTrue(wait_for(lambda: self.stats()["rejected"] >= 1))
        self.assertEqual(self.stats()["received"], 0)

    def test_garbage_ignored(self):
        self.audio.sendto(b"hello, this is not audio", self.dest)
        self.send(self.session, 0)
        self.assertTrue(wait_for(lambda: self.stats()["received"] == 1))

    def test_loss_and_late_counting(self):
        for seq in (0, 1, 5):
            self.send(self.session, seq)
        self.assertTrue(wait_for(lambda: self.stats()["received"] == 3))
        self.assertEqual(self.stats()["lost"], 3)
        self.send(self.session, 2)  # late
        self.assertTrue(wait_for(lambda: self.stats()["late"] == 1))

    def test_hello_while_connected_resends_accept(self):
        hello = P.encode_msg("hello", id="raw-1", name="Raw HP",
                             ctrl_port=self.ctrl.getsockname()[1])
        self.ctrl.sendto(hello, ("127.0.0.1", self.core.discovery_port))
        again = P.decode_msg(self.ctrl.recvfrom(2048)[0])
        self.assertEqual(again["t"], "accept")
        self.assertEqual(again["session"], self.session)

    def test_phone_cancel_before_connect_removes_device(self):
        other = P.encode_msg("hello", id="raw-2", name="Other Phone",
                             ctrl_port=self.ctrl.getsockname()[1])
        self.ctrl.sendto(other, ("127.0.0.1", self.core.discovery_port))
        self.assertTrue(wait_for(lambda: len(self.core.snapshot()["devices"]) == 2))
        self.ctrl.sendto(P.encode_msg("bye", id="raw-2", session=0),
                         ("127.0.0.1", self.core.discovery_port))
        self.assertTrue(wait_for(lambda: len(self.core.snapshot()["devices"]) == 1))


if __name__ == "__main__":
    unittest.main()
