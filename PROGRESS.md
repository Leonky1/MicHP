# Progress

Every checkpoint is delivered as a complete zip, so work can continue from the latest zip.

- [x] **CP1** protocol, PC core (discovery, connect, receive audio, gain, level, lost-packet count),
      CLI, fake phone
- [x] **CP2** output to the virtual mic (VB-Cable) + hear yourself + web UI design 1,
      Windows launchers (`install.bat`, `start.bat`). 34 tests pass on Linux; UI checked in
      headless Chromium (waiting, found, connected, no JS errors)
- [x] CP3 Android app (NOT yet compiled/tested)
- [x] CP4 guide (GUIDE.md)
- [x] **CP6** timers: connected time (PC) and mic-on time (phone). 53 tests pass on Linux
- [x] **CP5** look revisions: plain background (no gradient/glow/grid lines) on phone and PC; PC logo/icon
      rebuilt (square, 13 sizes); the Turn On Mic button on the phone moved up under the card; the installer
      also installs VB-Cable (only if missing, with an explanation). 50 tests pass on Linux
- [x] **CP7** revisions:
      1. PC: when the phone drops unexpectedly (audio timeout or the phone stops its mic), the connected
         time is frozen and kept on screen until the next Connect.
      2. Phone: the timer starts when Turn On Mic is pressed (even while still Connecting) and freezes
         when the mic is switched off.
      3. The whole app, installer, scripts and docs are now in English (the guide file is now GUIDE.md).
      63 tests pass on Linux (the Android code is still not compiled)

## Not tested yet (needs real devices)

- Broadcast on your home router
- Output to a Windows sound card / VB-Cable (tests only use a fake stream)
- Edge `--app` window on Windows (the fallback is the normal browser)
- The installer's automatic VB-Cable install (download, UAC, restart)
- The new icon in the Windows title bar/taskbar (DPI 100-175%)
- The Turn On Mic button in its new position (Compose not compiled)
- The new phone timer (start on switch-on, freeze on switch-off) and its English texts
- The Android app
