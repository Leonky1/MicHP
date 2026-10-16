# AGENTS.md — MicHP

Android phone -> Windows PC microphone app over home WiFi (UDP, no internet). User-facing language: plain, friendly English.
Full blueprint: `docs/BLUEPRINT.md`. Protocol: `PROTOCOL.md`.

## Commands
- PC tests (63 tests, must be green before finishing): `cd pc && python3 -m unittest discover -s tests -t .`
- Run the UI without audio/window: `cd pc && python3 -m michp_pc --no-browser --no-audio --port 8799`
- Fake phone for testing: `python -m michp_pc.fake_phone`
- Windows build: `pc/build.bat` (Windows only). Android: Android Studio, package `com.michp`.

## Rules
1. Protocol = contract. Change `PROTOCOL.md`, `pc/michp_pc/protocol.py`, `android/.../net/Protocol.kt` together.
2. Python: stdlib + `sounddevice` + `pywebview`. Plain threads + sockets, **no** asyncio, **no** `audioop`.
3. The local UI listens on `127.0.0.1` only. Keep the Host/Origin/`X-MicHP` checks, the 4096 body limit, and render device names with `textContent`.
4. Product name is **MicHP** (capital HP). Internal identifiers use the same name: `michp_pc`, `com.michp`, `X-MicHP`. Change them all together.
5. Features that were REMOVED on purpose, do not bring them back: noise detection and the "low sound" status.
6. UI text is English, plain and friendly (the app is for international users; do not mix languages); design is dark-blue glass (tokens in `static/style.css`). Text must not be selectable.
   Background is **plain** `#050A1E` on PC and phone: no gradient, glow or grid lines (gradients are only allowed inside the logo/app icon).
7. Monitor ("hear yourself") must not open a second stream to the same device as the virtual mic output.
8. Do not claim something "works" if it was not tested. Verified on real devices by the author: Android app (compiled, phone), installer + automatic VB-Cable install, sound in other apps through CABLE Output, volume, 125%+ scaling, phone screen off. Still not proven: other routers (AP isolation), other phones/Android versions, the Edge fallback window, measured latency.
9. Logo: single source `branding/logo.svg` (copy it identically to `pc/michp_pc/static/logo.svg`). Do not scale/crop the logo in CSS; `.logo` must be square with no `border-radius`. `michp.ico` must contain square frames (16, 20, 24, 28, 32, 40, 48, 56, 64, 256 at least). Copy it to `pc/michp.ico` and `branding/michp.ico` (must be identical).
10. Installer (`pc/installer.iss`) installs VB-Cable automatically with no checkbox: a plain-language info page shows only if it is not installed yet, then one click on Install installs MicHP + VB-Cable; download it from vb-audio.com (do not bundle it in the repo), ask for Administrator, then ask for a restart. If it fails, MicHP is still installed.
11. Phone: the action button sits under the status card (not stuck to the bottom of the screen).
12. Timers (counted locally with a monotonic clock, **no protocol change**, and no extra rows that make the layout shift when the status changes):
    - PC = connected time (`connected_seconds`, from the first audio packet). If the connection ends on its own (audio timeout `lost`, or the phone sent `bye` -> `phone`) the time is frozen in `last_session_seconds` / `last_session_reason` and stays on screen until the next Connect. A manual Disconnect on the PC clears it.
    - Phone = time since the mic was switched on (`activeSinceMs`, set when the service enters Connecting, i.e. when the button is pressed, whether or not it is connected yet). When the mic is switched off (by the user, the PC or an error) it freezes into `frozenMs` and shows "Last session HH:MM:SS" until the next start. Going Online must not touch the timer.

## Gotchas
- `pkill -f michp_pc` in the sandbox can kill your own shell; stop processes by PID.
- After changing the name/icon, run `build.bat` again so the installer changes too.
- Rebuilding `michp.ico`: render the SVG to a PNG per size with Chromium (Playwright, transparent background) and assemble the ICO yourself; `branding/logo-small.svg` is used for sizes <= 32 px. Do not use `Image.save(..., sizes=...)` from one big image (blurry/cropped at small sizes).
- In Inno Pascal strings a single quote is doubled (`''`); be careful when writing PowerShell commands in `[Code]`.
- `pc/tests/test_assets.py` fails if Indonesian words creep back into the repo (docs, UI, code).
