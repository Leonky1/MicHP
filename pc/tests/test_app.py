import json
import os
import tempfile
import unittest

from michp_pc import app

SCREEN = (0, 0, 1920, 1080)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "window.json")

    def test_missing_file_gives_none(self):
        self.assertIsNone(app.load_geometry(self.path, SCREEN))

    def test_roundtrip(self):
        g = {"x": 100, "y": 80, "width": 1000, "height": 700}
        app.save_geometry(g, self.path)
        self.assertEqual(app.load_geometry(self.path, SCREEN), g)

    def test_corrupt_file_ignored(self):
        with open(self.path, "w") as f:
            f.write("{bad")
        self.assertIsNone(app.load_geometry(self.path, SCREEN))

    def test_absurd_size_ignored(self):
        app.save_geometry({"x": 0, "y": 0, "width": 50, "height": 50}, self.path)
        self.assertIsNone(app.load_geometry(self.path, SCREEN))

    def test_window_on_unplugged_monitor_ignored(self):
        app.save_geometry({"x": 3000, "y": 100, "width": 900, "height": 640}, self.path)
        self.assertIsNone(app.load_geometry(self.path, SCREEN))
        app.save_geometry({"x": -2500, "y": 100, "width": 900, "height": 640}, self.path)
        self.assertIsNone(app.load_geometry(self.path, SCREEN))

    def test_partially_visible_window_kept(self):
        g = {"x": 1500, "y": 200, "width": 900, "height": 640}
        app.save_geometry(g, self.path)
        self.assertEqual(app.load_geometry(self.path, SCREEN), g)


if __name__ == "__main__":
    unittest.main()
