# MicHP

Turn an Android phone into a microphone for a Windows PC over home WiFi (no internet, no app store).

- `PROTOCOL.md` - how the phone and PC talk to each other
- `GUIDE.md` - user guide (install, use, troubleshooting)
- `pc/` - PC software (Python + local web UI)

## PC software (Windows)

One time only:
1. Install Python 3.9+ from python.org (tick "Add python to PATH").
2. **VB-Cable** (virtual mic, vb-audio.com/Cable) makes the phone's sound show up as a microphone in Windows.
   If you use the `MicHP-Setup.exe` installer, VB-Cable is installed automatically (skipped if it is
   already there). If you use the `install.bat` way, install VB-Cable manually and restart the PC.
3. In the `pc` folder, double-click `install.bat`.

Every time you use it: double-click `start.bat`. The MicHP window opens (Edge app mode).
Do not close the black (console) window while MicHP is in use.

In Discord/OBS/Zoom, pick **CABLE Output** as the microphone.
The **Output** dropdown at the top right must point to **CABLE Input**
(selected automatically if VB-Cable is installed).

**Hear yourself** plays the sound from the phone on the Windows default output (headphones).
Use a headset; with speakers you will get an echo.
**Mic volume**: 50% = original volume, 100% = 2x louder.

**Timers.** The PC shows how long the phone has been connected. If the phone drops unexpectedly
(or stops its mic), the time freezes and stays on screen until the next Connect. The phone shows how
long its mic has been switched on, starting the moment you tap **Turn On Mic** (even while it is
still connecting), and freezes it when you switch the mic off.

Windows Firewall will ask for permission the first time. Choose **Private networks**.

## Testing without a phone

```
cd pc
python -m unittest discover -s tests -t . -v        # all 63 tests must be OK
python -m michp_pc --no-audio                      # open the UI without audio output
python -m michp_pc.fake_phone --seconds 10         # fake phone (in another terminal)
```

Terminal version without the UI: `python -m michp_pc.cli --auto --record test.wav`.
