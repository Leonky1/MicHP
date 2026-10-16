# MicHP Guide (home use, Windows + Android)

## 1. Set up the PC (one time)
1. **Virtual mic (VB-Cable)** — this is what lets the phone's sound be picked as a microphone in Discord/games. You do not need to install it separately: the MicHP installer (step 2) installs it for you.
   - If VB-Cable is **already there**, it is skipped and not installed again.
   - If it is **not there**, the installer shows a short explanation, then you click **Install**: MicHP is installed, VB-Cable is downloaded from vb-audio.com (needs internet for a moment), Windows asks for Administrator permission and "Install this device software?" → choose **Install**, then **restart the PC** at the end.
   - If it fails or is skipped, MicHP is still installed; install it manually from vb-audio.com/Cable (right-click `VBCABLE_Setup_x64.exe` → Run as administrator) and restart.
2. **Turn it into an app** (needs Python 3.10+ only to build the installer, tick "Add python.exe to PATH"):
   extract the zip, go into the `pc` folder, double-click **`build.bat`**.
   - If **Inno Setup 6 or 7** (free, jrsoftware.org) is installed: the result is `pc\installer\MicHP-Setup.exe`. Double-click it, install, then open **MicHP** from the Start Menu / Desktop. After that Python is no longer needed.
   - If not: the app is still built at `pc\dist\MicHP\MicHP.exe` (usable right away; do not move only part of the folder).
3. Open **MicHP**. The app opens its own window (it uses WebView2, included in Windows 11 and up-to-date Windows 10; if it is missing it falls back to an Edge window automatically). Closing the window closes the app.
4. When Windows Firewall asks, **allow it on Private networks**. If you missed it, see Troubleshooting.

(The old way without the installer still works: `install.bat`, then `start.bat`.)

## 2. Set up the phone (one time)
Follow `android/README.md` (Android Studio → new project → copy the files → Run / Build APK).
To install the APK without a cable: send the APK to the phone and allow "Install from unknown sources".

## 3. Use it
1. PC: open MicHP (or `start.bat`). In your app/game/Discord, pick the **CABLE Output** mic.
2. Phone: open MicHP → **Turn On Mic** → yellow "Mic Connecting..".
3. PC: the phone's name shows up → **Connect** → the phone turns green "Mic Online".
4. Timers:
   - **PC — Connected**: how long the phone has been connected (counted from the first audio). If the connection drops unexpectedly (the WiFi dies, or the phone stops its mic) the time **freezes** and stays on screen in yellow ("Connection lost after 00:12:34") until you connect again. Clicking **Disconnect** yourself clears it.
   - **Phone — Active for**: starts the moment you tap **Turn On Mic**, even while it is still "Connecting.." and whether or not the PC has connected yet. When you switch the mic off (**Turn Off Mic** / **Cancel**, or the PC ends the connection) it **freezes** and shows "Last session 00:12:34" until you turn the mic on again, which starts from 00:00:00.
5. Adjust the volume, watch the sound bar, and turn on "Hear yourself" to test (use a headset to avoid feedback).

## 3b. Using it in Discord (and other apps)
MicHP does not create its own microphone device in Windows (that needs a special driver). It uses **VB-Cable**, so in Discord the mic is named **"CABLE Output (VB-Audio Virtual Cable)"**, not "MicHP".
1. Make sure VB-Cable is installed (through the MicHP installer or manually) and the PC has been restarted. In MicHP, the **Output** box (top right) must show **CABLE Input**, and the yellow "Virtual mic (VB-Cable) not found" warning must not be there.
2. Discord → User Settings → Voice & Video → **Input Device** → pick **CABLE Output**.
3. If it does not show up: quit Discord completely (right-click its tray icon → Quit) and open it again.
4. **Want the name to be "MicHP" in the list?** Windows: Settings → System → Sound → More sound settings / Sound control panel → **Recording** tab → right-click **CABLE Output** → Properties → change the name in the text box → OK → restart Discord.
5. In Discord, automatic Echo Cancellation / Noise Suppression can cut your voice off; try turning them off if the sound is choppy.

## 4. First-test checklist (in order, stop at the step that fails)
- [ ] PC & phone are on the same WiFi (not a guest network, VPN off)
- [ ] `start.bat` runs with no red errors
- [ ] The VB-Cable warning in the UI is gone
- [ ] The phone's name shows up on the PC while it is Connecting
- [ ] Click Connect → the phone turns green
- [ ] The sound bar moves when you talk
- [ ] "Hear yourself" is audible
- [ ] In Windows > Sound > Recording, CABLE Output moves
- [ ] The phone timer starts as soon as you tap Turn On Mic and freezes when you turn it off
- [ ] Switch the phone's screen off for 2 minutes, the sound keeps going

## 5. Troubleshooting
| Symptom | Common cause | Fix |
|---|---|---|
| The phone's name does not show up | The router/AP has *client isolation* / AP isolation turned on; or the firewall | Turn off AP isolation on the router; allow Python in the firewall (UDP 48100–48102) |
| The phone's name does not show up (dual-band WiFi) | The phone is on 5 GHz and the PC on LAN/2.4 GHz, which are on different segments on some routers | Use the same band or the same segment |
| Stays yellow after Connect | The firewall blocks the accept reply to the phone | Make sure the PC's network type is Private |
| Green but no sound in the app | The app uses the default mic, not CABLE Output | Pick CABLE Output in the target app |
| Choppy sound | Busy 2.4 GHz WiFi | Use 5 GHz, move the phone closer to the router |
| The mic turns off by itself when the screen is off | The phone maker's battery saver | Phone Settings → Battery → MicHP → "Unrestricted" |
| The PC timer froze and says "Connection lost after ..." | The audio stopped for 3 seconds (WiFi dropped, phone locked/killed the app, or the mic was switched off) | Check the WiFi / battery saver, then tap Turn On Mic again and click Connect; the frozen time clears when you connect again |
| You hear yourself even with "Hear yourself" off, or doubled | (a) the Output box in MicHP is not CABLE Input, (b) in Windows → Sound → Recording → CABLE Output → Properties → Listen tab, "Listen to this device" is ticked, or (c) your Windows default speaker is CABLE Input | (a) pick CABLE Input in Output (MicHP now warns you); (b) untick it; (c) change the Windows default output device to your real speakers/headphones |
| There is an echo | "Hear yourself" is on without a headset | Turn it off or use a headset |

## 6. Known limitations
- Home LAN only, no encryption (anyone on the same WiFi can send hello; the PC still needs a click on Connect).
- Raw PCM audio, about 770 kbps, no compression.
- One active phone at a time.
- The phone's timer (start on switch-on, freeze on switch-off) has not been tested on a real device (Compose has not been compiled).
- The window position and size are remembered (`%LOCALAPPDATA%\\MicHP\\window.json`); on screens with 125–150% scaling this is untested.
- Latency is about 60–150 ms; not measured on real devices yet.
- The installer's automatic VB-Cable install (detection, download, Administrator permission) has **never been run on Windows**; the new icon (small sizes in the taskbar/title bar) has also not been seen on Windows.
- The installer/`build.bat` has **never been run on Windows** (I only tested the PyInstaller build on Linux: the UI files are bundled and the server runs). The standalone window (pywebview/WebView2), the Edge window fallback, and the close button are also untested on Windows.
- **Not tested on real devices:** the Android app (never compiled), broadcast on your home router, VB-Cable, the Edge window. Only the PC side is tested automatically (63 tests, loopback).
