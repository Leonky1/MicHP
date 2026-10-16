import http.client
import json
import threading
import time
import unittest

from michp_pc.audio_out import AudioOutput
from michp_pc.core import PcCore
from michp_pc.fake_phone import run_fake_phone
from michp_pc.webui import App, make_server

from .test_audio import DEVICES, FakeSD
from .test_integration import wait_for


class WebUiTests(unittest.TestCase):
    def setUp(self):
        self.core = PcCore(discovery_port=0, audio_port=0, bind_ip="127.0.0.1",
                           audio_timeout=1.0)
        self.core.start()
        self.sd = FakeSD(DEVICES)
        self.audio = AudioOutput(sd=self.sd)
        self.audio.start()
        self.core.on_audio = self.audio.push
        self.server = make_server(App(self.core, self.audio), port=0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.phone_thread = None

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.core.stop()
        self.audio.stop()
        if self.phone_thread:
            self.phone_thread.join(timeout=2)

    def call(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        h = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body)
            h.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=data, headers=h)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, raw

    def post(self, path, body):
        return self.call("POST", path, body, {"X-MicHP": "1"})

    def start_phone(self, **kw):
        kw["discovery_port"] = self.core.discovery_port
        self.phone_thread = threading.Thread(
            target=lambda: run_fake_phone(**kw), daemon=True)
        self.phone_thread.start()

    def test_static_files_served(self):
        for path, marker in (("/", b"MicHP"), ("/app.js", b"api/state"),
                             ("/style.css", b"--accent")):
            status, raw = self.call("GET", path)
            self.assertEqual(status, 200, path)
            self.assertIn(marker, raw)

    def test_no_path_traversal(self):
        self.assertEqual(self.call("GET", "/../core.py")[0], 404)
        self.assertEqual(self.call("GET", "/%2e%2e/core.py")[0], 404)

    def test_state_machine_over_http(self):
        status, s = self.call("GET", "/api/state")
        self.assertEqual((status, s["state"]), (200, "waiting"))
        self.assertEqual(s["gain_percent"], 50)
        self.assertEqual(s["audio"]["virtual_name"], "CABLE Input (VB-Audio Virtual Cable)")

        self.start_phone(seconds=4.0, amp=0.5, name="HP Ferdi")
        self.assertTrue(wait_for(lambda: self.call("GET", "/api/state")[1]["state"] == "found"))
        s = self.call("GET", "/api/state")[1]
        self.assertEqual(s["devices"][0]["name"], "HP Ferdi")

        status, r = self.post("/api/connect", {"id": s["devices"][0]["id"]})
        self.assertEqual((status, r["ok"], r["state"]["state"]), (200, True, "connected"))
        self.assertTrue(wait_for(lambda: self.call("GET", "/api/state")[1]["level"] > 0.5))

        status, r = self.post("/api/gain", {"percent": 100})
        self.assertEqual(r["state"]["gain_percent"], 100)
        self.assertEqual(self.core.gain, 2.0)

        status, r = self.post("/api/monitor", {"on": True})
        self.assertTrue(r["ok"])
        self.assertTrue(r["state"]["audio"]["monitor"])

        status, r = self.post("/api/disconnect", {})
        self.assertNotEqual(r["state"]["state"], "connected")

    def test_post_requires_custom_header_and_local_origin(self):
        self.assertEqual(self.call("POST", "/api/disconnect", {})[0], 403)
        bad = {"X-MicHP": "1", "Origin": "http://evil.example"}
        self.assertEqual(self.call("POST", "/api/disconnect", {}, bad)[0], 403)
        good = {"X-MicHP": "1", "Origin": "http://127.0.0.1:%d" % self.port}
        self.assertEqual(self.call("POST", "/api/disconnect", {}, good)[0], 200)

    def test_wrong_host_header_rejected(self):
        status, _ = self.call("GET", "/api/state", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)

    def test_bad_input_rejected(self):
        self.assertEqual(self.post("/api/gain", {"percent": "abc"})[0], 400)
        self.assertEqual(self.post("/api/output", {"index": "1"})[0], 400)
        self.assertEqual(self.post("/api/nope", {})[0], 404)
        status, _ = self.call("POST", "/api/gain", None, {"X-MicHP": "1"})
        # empty body -> percent None -> must be 400
        self.assertEqual(status, 400)

    def test_select_output_device(self):
        status, r = self.post("/api/output", {"index": None})
        self.assertIsNone(r["state"]["audio"]["virtual_index"])
        status, r = self.post("/api/output", {"index": 1})
        self.assertEqual(r["state"]["audio"]["virtual_index"], 1)


if __name__ == "__main__":
    unittest.main()
