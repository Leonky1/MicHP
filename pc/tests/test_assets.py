"""Asset & static UI tests: plain background, square logo, installer + VB-Cable, English-only text."""
import io
import os
import re
import struct
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.dirname(HERE)
ROOT = os.path.dirname(PC)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class BackgroundTests(unittest.TestCase):
    def test_css_has_no_gradient_or_grid(self):
        css = read("pc", "michp_pc", "static", "style.css")
        self.assertNotIn("gradient", css)
        self.assertNotIn("--glow", css)
        self.assertNotIn("body::before", css)
        self.assertRegex(css, r"body \{[^}]*background: var\(--bg\);")

    def test_android_background_is_solid(self):
        kt = read("android", "app", "src", "main", "java", "com", "michp", "ui", "MicHPScreen.kt")
        self.assertNotIn("Brush", kt)
        self.assertNotIn("Gradient", kt)


ANDROID = ("android", "app", "src", "main", "java", "com", "michp")


class UptimeUiTests(unittest.TestCase):
    def test_pc_shows_connected_time(self):
        self.assertIn('id="uptime"', read("pc", "michp_pc", "static", "index.html"))
        js = read("pc", "michp_pc", "static", "app.js")
        self.assertIn("s.connected_seconds", js)
        self.assertIn("fmtDuration", js)

    def test_pc_shows_frozen_time_without_shifting_layout(self):
        html = read("pc", "michp_pc", "static", "index.html")
        self.assertIn('id="lastWaiting"', html)
        self.assertIn('id="lastFound"', html)
        js = read("pc", "michp_pc", "static", "app.js")
        self.assertIn("s.last_session_seconds", js)
        css = read("pc", "michp_pc", "static", "style.css")
        # the row always keeps its space: hidden with visibility, never display:none
        self.assertRegex(css, r"\.uptime\.last \{ visibility: hidden; \}")
        self.assertNotRegex(css, r"\.uptime\.last[^}]*display:\s*none")

    def test_phone_timer_starts_when_mic_is_switched_on(self):
        service = read(*ANDROID, "MicService.kt")
        self.assertIn("activeSinceMs = SystemClock.elapsedRealtime()", service)  # on the Connecting state
        client = read(*ANDROID, "net", "MicClient.kt")
        # going Online must not restart or alter the timer
        online = re.search(r"status = MicStatus\.Online[^\n]*", client).group(0)
        self.assertNotIn("activeSinceMs", online)
        self.assertNotIn("onlineSinceMs", client + service)

    def test_phone_timer_freezes_when_mic_is_switched_off(self):
        client = read(*ANDROID, "net", "MicClient.kt")
        self.assertIn("frozenMs = frozen", client)
        repo = read(*ANDROID, "MicRepository.kt")
        self.assertIn("val frozenMs: Long?", repo)
        kt = read(*ANDROID, "ui", "MicHPScreen.kt")
        self.assertIn("Active for ", kt)
        self.assertIn("state.frozenMs", kt)
        self.assertIn("activeSinceMs", kt)


class EnglishOnlyTests(unittest.TestCase):
    """The app and its docs are English only (international users)."""

    WORDS = re.compile(
        r"\b(yang|tidak|untuk|dengan|kalau|sudah|belum|jangan|pakai|karena|supaya|bisa|harus|"
        r"setelah|sebelum|ketika|muncul|jendela|tombol|suara|nyalakan|matikan|batalkan|menunggu|"
        r"tersambung|aktif|panduan|hanya|sudah|dulu)\b", re.I)
    SUFFIXES = (".py", ".kt", ".js", ".html", ".css", ".md", ".iss", ".bat", ".xml", ".txt", ".svg")

    def test_no_indonesian_left(self):
        found = []
        this = os.path.abspath(__file__)
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "build", "dist", ".venv-build")]
            for name in files:
                path = os.path.join(base, name)
                if not name.endswith(self.SUFFIXES) or os.path.abspath(path) == this:
                    continue
                with open(path, encoding="utf-8", errors="replace") as f:
                    for n, line in enumerate(f, 1):
                        m = self.WORDS.search(line)
                        if m:
                            found.append("%s:%d: %s" % (os.path.relpath(path, ROOT), n, m.group(0)))
        self.assertEqual(found, [], "\n".join(found[:20]))

    def test_ui_declares_english(self):
        self.assertIn('<html lang="en">', read("pc", "michp_pc", "static", "index.html"))


class LogoTests(unittest.TestCase):
    def test_pc_logo_is_square_and_same_as_branding(self):
        svg = read("pc", "michp_pc", "static", "logo.svg")
        self.assertEqual(svg, read("branding", "logo.svg"))
        self.assertIn('viewBox="0 0 512 512"', svg)

    def test_header_logo_keeps_square_size(self):
        css = read("pc", "michp_pc", "static", "style.css")
        logo = re.search(r"\.logo \{([^}]*)\}", css).group(1)
        self.assertIn("flex: 0 0 36px", logo)
        self.assertIn("aspect-ratio: 1 / 1", logo)
        self.assertNotIn("border-radius", logo)  # extra radius would clip the logo corners

    def test_ico_frames_are_square_png_and_cover_dpi_sizes(self):
        for rel in (("pc", "michp.ico"), ("branding", "michp.ico")):
            with open(os.path.join(ROOT, *rel), "rb") as f:
                d = f.read()
            _, kind, n = struct.unpack("<HHH", d[:6])
            self.assertEqual(kind, 1)
            sizes = set()
            for i in range(n):
                w, h, _c, _r, _p, _b, size, off = struct.unpack("<BBBBHHII", d[6 + 16 * i:22 + 16 * i])
                w, h = w or 256, h or 256
                self.assertEqual(w, h)
                png = d[off:off + size]
                self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
                pw, ph = struct.unpack(">II", png[16:24])
                self.assertEqual((pw, ph), (w, h))  # content matches the size in the header: not force-scaled
                sizes.add(w)
            for need in (16, 20, 24, 28, 32, 40, 48, 56, 64, 256):  # 100%-175% DPI + Explorer
                self.assertIn(need, sizes)
        with open(os.path.join(PC, "michp.ico"), "rb") as a, open(os.path.join(ROOT, "branding", "michp.ico"), "rb") as b:
            self.assertEqual(a.read(), b.read())


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.iss = read("pc", "installer.iss")

    def test_cable_is_automatic_and_skipped_when_present(self):
        self.assertNotIn("installcable", self.iss)  # no checkbox: one click on Install = MicHP + VB-Cable
        self.assertRegex(self.iss, r"ssPostInstall\) and \(not WizardSilent\) and \(not CableInstalled\)")
        self.assertIn("Result := CableInstalled or WizardSilent", self.iss)  # already present -> page skipped
        self.assertIn("UpdateReadyMemo", self.iss)

    def test_cable_comes_from_official_site_and_needs_admin_prompt(self):
        self.assertIn("https://download.vb-audio.com/", self.iss)
        self.assertIn("ShellExec('runas'", self.iss)
        self.assertIn("NeedRestart", self.iss)

    def test_info_page_explains_purpose(self):
        self.assertIn("CABLE Output", self.iss)
        self.assertIn("virtual mic", self.iss.lower())


if __name__ == "__main__":
    unittest.main()
