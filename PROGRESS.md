# Progress

Every checkpoint is delivered as a complete zip, so work can continue from the latest zip.

- [x] **CP1** protocol, PC core (discovery, connect, receive audio, gain, level, lost-packet count),
      CLI, fake phone
- [x] **CP2** output to the virtual mic (VB-Cable) + hear yourself + web UI design 1,
      Windows launchers (`install.bat`, `start.bat`). 34 tests pass on Linux; UI checked in
      headless Chromium (waiting, found, connected, no JS errors)
- [x] CP3 Android app (compiled and tested on a real phone by the author)
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
      63 tests pass on Linux

## Tested on real devices (by the author)

- Android app: compiled, installed and used on a real phone (APK)
- Windows installer (`MicHP-Setup.exe`), including the automatic VB-Cable install
- Phone found on the home WiFi, Connect works, sound reaches other apps through CABLE Output
- Clear sound, almost no noticeable delay, adjustable mic volume
- Screen scaling of 125% or more, and the phone's screen switched off

## Not tested yet

- Other routers (especially ones with AP/client isolation), other phones and Android versions
- The Edge `--app` fallback window (used only when WebView2 is missing)
- Latency has not been measured with an instrument (it only feels almost instant)
