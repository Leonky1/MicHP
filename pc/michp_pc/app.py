"""PC software launcher: python -m michp_pc"""

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser

from . import protocol as P
from .audio_out import AudioOutput
from .core import PcCore
from .webui import App, make_server

BROWSER_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
APP_NAME = "MicHP"


def data_dir():
    """App data folder (log, window profile)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "MicHP")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def log_error(msg):
    """Write to %LOCALAPPDATA%\\MicHP\\michp.log (an exe without a console has no terminal)."""
    print(msg)
    try:
        with open(os.path.join(data_dir(), "michp.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  " + msg + "\n")
    except OSError:
        pass


def say(msg):
    """Show a message to the user: a dialog box on Windows, the terminal elsewhere."""
    print(msg)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, APP_NAME, 0x40)
        except Exception:
            pass


def open_window(url):
    """Open the UI as an app window (Edge/Chrome --app).

    Returns the window process (Popen) on success; None if it fell back to the normal browser.
    """
    if sys.platform == "win32":
        for exe in BROWSER_PATHS:
            if os.path.exists(exe):
                try:
                    return subprocess.Popen([
                        exe, "--app=" + url, "--window-size=900,640",
                        # own profile: this window is a separate process, so we know when it is closed
                        "--user-data-dir=" + os.path.join(data_dir(), "window-profile"),
                        "--no-first-run", "--no-default-browser-check", "--disable-sync",
                    ])
                except OSError:
                    break
    webbrowser.open(url)
    return None


APP_ID = "MicHP.App"
DEFAULT_SIZE = (900, 640)
MIN_SIZE = (800, 580)


def resource_path(name):
    """Location of bundled files, from the source tree or from the PyInstaller .exe."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _geometry_file():
    return os.path.join(data_dir(), "window.json")


def _screen_rect():
    """(x, y, width, height) of all monitors combined; None if unknown."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        gm = ctypes.windll.user32.GetSystemMetrics
        return gm(76), gm(77), gm(78), gm(79)  # SM_X/Y/CX/CYVIRTUALSCREEN
    except Exception:
        return None


def load_geometry(path=None, screen=None):
    """Last window position & size; None if missing / not plausible."""
    import json
    try:
        with open(path or _geometry_file(), "r", encoding="utf-8") as f:
            g = json.load(f)
        x, y, w, h = (int(g[k]) for k in ("x", "y", "width", "height"))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not (MIN_SIZE[0] <= w <= 5000 and MIN_SIZE[1] <= h <= 4000):
        return None
    scr = screen if screen is not None else _screen_rect()
    if scr is not None:
        sx, sy, sw, sh = scr
        # part of the window must still be visible (the monitor may have been unplugged)
        if x + 120 > sx + sw or x + w - 120 < sx or y + 60 > sy + sh or y < sy - 20:
            return None
    return {"x": x, "y": y, "width": w, "height": h}


def save_geometry(g, path=None):
    import json
    try:
        with open(path or _geometry_file(), "w", encoding="utf-8") as f:
            json.dump({k: int(g[k]) for k in ("x", "y", "width", "height")}, f)
    except (OSError, ValueError, KeyError, TypeError):
        pass


def _windows_identity():
    """Make the taskbar treat this as its own MicHP app (own icon, can be pinned)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def _apply_window_icon(title):
    """Put the MicHP icon on the window (top-left corner + taskbar)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        ico = resource_path("michp.ico")
        hwnd = 0
        for _ in range(20):  # the new window shows up shortly
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                break
            time.sleep(0.15)
        if not hwnd or not os.path.exists(ico):
            return
        from ctypes import c_size_t, c_uint, c_void_p
        user32.LoadImageW.restype = c_void_p
        user32.SendMessageW.argtypes = [c_void_p, c_uint, c_size_t, c_void_p]
        IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
        # ICON_SMALL=0 (SM_CXSMICON=49), ICON_BIG=1 (SM_CXICON=11): size follows the screen scale
        for which, metric, fallback in ((0, 49, 16), (1, 11, 32)):
            size = user32.GetSystemMetrics(metric) or fallback
            h = user32.LoadImageW(None, ico, IMAGE_ICON, size, size, LR_LOADFROMFILE)
            if h:
                user32.SendMessageW(hwnd, WM_SETICON, which, h)
    except Exception:
        pass


def run_native_window(url):
    """Standalone app window (not a browser tab/window) via pywebview + WebView2.

    Window position and size are remembered. Returns True if the window was shown and then
    closed by the user, False if it could not be used.
    """
    try:
        import webview
    except Exception:
        import traceback
        log_error("Standalone window: pywebview could not be imported, using the Edge fallback.\n" + traceback.format_exc())
        return False
    _windows_identity()
    geo = load_geometry()
    state = dict(geo) if geo else None
    kw = {}
    if geo:
        kw = dict(x=geo["x"], y=geo["y"], width=geo["width"], height=geo["height"])
    else:
        kw = dict(width=DEFAULT_SIZE[0], height=DEFAULT_SIZE[1])
    try:
        window = webview.create_window(APP_NAME, url, min_size=MIN_SIZE,
                                       background_color="#050A1E", text_select=False, **kw)
        cur = state or {"x": 0, "y": 0, "width": kw["width"], "height": kw["height"]}
        have_pos = bool(geo)

        def on_moved(x, y):
            nonlocal have_pos
            cur["x"], cur["y"] = x, y
            have_pos = True
            save_geometry(cur)

        def on_resized(width, height):
            cur["width"], cur["height"] = width, height
            if have_pos:
                save_geometry(cur)

        def on_shown():
            threading.Thread(target=_apply_window_icon, args=(APP_NAME,), daemon=True).start()

        def on_closing():
            # save the last position & size when the window closes (backup for resize-only changes)
            try:
                if window.width >= MIN_SIZE[0] and window.height >= MIN_SIZE[1]:
                    save_geometry({"x": window.x, "y": window.y,
                                   "width": window.width, "height": window.height})
            except Exception:
                pass

        for name, fn in (("moved", on_moved), ("resized", on_resized), ("shown", on_shown),
                         ("closing", on_closing)):
            try:
                getattr(window.events, name).__iadd__(fn)
            except Exception:
                pass
        webview.start(gui="edgechromium", storage_path=os.path.join(data_dir(), "webview"))
        return True
    except Exception:  # WebView2 runtime missing, etc.
        import traceback
        log_error("Standalone window failed, using the Edge fallback.\n" + traceback.format_exc())
        return False


def _wait_window(proc):
    """Wait for the Edge/Chrome window to close. False if the process ended right away (hand-off)."""
    started = time.monotonic()
    proc.wait()
    return time.monotonic() - started >= 3


def _wait(thread):
    while thread.is_alive():
        thread.join(0.5)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="michp_pc", description="MicHP - PC software")
    ap.add_argument("--port", type=int, default=8765, help="local UI port")
    ap.add_argument("--no-browser", action="store_true", help="do not open a window automatically")
    ap.add_argument("--no-audio", action="store_true", help="no audio output (UI testing only)")
    ap.add_argument("--discovery-port", type=int, default=P.DISCOVERY_PORT)
    ap.add_argument("--audio-port", type=int, default=P.AUDIO_PORT)
    args = ap.parse_args(argv)
    log_error("MicHP started (python %s, frozen=%s)" % (sys.version.split()[0], bool(getattr(sys, "frozen", False))))

    core = PcCore(discovery_port=args.discovery_port, audio_port=args.audio_port)
    audio = AudioOutput(sd=None if not args.no_audio else _NoSound())
    try:
        core.start()
    except OSError as e:
        # most likely MicHP is already running: just show its window
        if _ui_alive(args.port):
            log_error("Another MicHP is already running on port %d (%s). Showing its window. "
                      "If it is a stuck old process, close MicHP.exe in Task Manager." % (args.port, e))
            if not args.no_browser:
                existing = "http://127.0.0.1:%d/" % args.port
                if not run_native_window(existing):
                    open_window(existing)
            return 0
        say("Network ports %d/%d cannot be used:\n%s\n\nClose any other program using them, "
            "or check the Firewall." % (args.discovery_port, args.audio_port, e))
        return 1
    try:
        server = make_server(App(core, audio), port=args.port)
    except OSError as e:
        core.stop()
        say("UI port %d cannot be used:\n%s" % (args.port, e))
        return 1

    audio.start()
    core.on_audio = audio.push
    if audio.available and audio.info()["virtual_index"] is None:
        print("Virtual mic (CABLE Input) not found. Run the MicHP installer again (it installs VB-Cable too) or install VB-Cable from vb-audio.com/Cable, then restart the PC.")
    if audio.error:
        print("Audio:", audio.error)

    url = "http://127.0.0.1:%d/" % server.server_address[1]
    print("MicHP is running at %s  (close its window to stop)" % url)
    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()
    try:
        if args.no_browser:
            _wait(srv_thread)
        elif not run_native_window(url):
            # WebView2 / pywebview missing -> fallback: Edge/Chrome app-mode window
            say("The standalone MicHP window could not be opened, so it was opened through Edge instead.\n\n"
                "The reason is logged in:\n" + os.path.join(data_dir(), "michp.log"))
            proc = open_window(url)
            if proc is not None and _wait_window(proc):
                pass  # window closed = done
            else:
                _wait(srv_thread)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        core.stop()
        audio.stop()
    return 0


def _ui_alive(port):
    """True if a MicHP is already serving the UI on this port."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/state" % port, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


class _NoSound:
    """Empty stand-in for sounddevice when using --no-audio."""

    class default:
        hostapi = 0

    @staticmethod
    def query_devices():
        return []

    @staticmethod
    def RawOutputStream(**kw):
        raise RuntimeError("audio is turned off")


if __name__ == "__main__":
    sys.exit(main())
