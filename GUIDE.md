# MicHP Guide (home use, Windows + Android)

## 1. Set up the PC (one time)
1. **Virtual mic (VB-Cable)** — this is what lets the phone's sound be picked as a microphone in Discord/games. You do not need to install it separately: the MicHP installer (step 2) installs it for you.
   - If VB-Cable is **already there**, it is skipped and not installed again.
   - If it is **not there**, the installer shows a short explanation, then you click **Install**: MicHP is installed, VB-Cable is downloaded from vb-audio.com (needs internet for a moment), Windows asks for Administrator permission and "Install this device software?" → choose **Install**, then **restart the PC** at the end.
   - If it fails or is skipped, MicHP is still installed; install it manually from vb-audio.com/Cable (right-click `VBCABLE_Setup_x64.exe` → Run as administrator) and restart.
2. **Install MicHP**: download **`MicHP-Setup.exe`** from the GitHub Releases page, double-click it and install, then open **MicHP** from the Start Menu / Desktop. Python is not needed.
   - *Developers:* to build the installer yourself, install Python 3.10+ and Inno Setup 6 or 7 (free, jrsoftware.org), then double-click **`pc/build.bat`**. The result is `pc\installer\MicHP-Setup.exe`. Without Inno Setup the app is still built at `pc\dist\MicHP\MicHP.exe`.
3. Open **MicHP**. The app opens its own window (it uses WebView2, included in Windows 11 and up-to-date Windows 10; if it is missing it falls back to an Edge window automatically). Closing the window closes the app.
4. When Windows Firewall asks, **allow it on Private networks**. If you missed it, see Troubleshooting.

(The old way without the installer still works: `install.bat`, then `start.bat`.)

## 2. Set up the phone (one time)
1. On the phone, download **`MicHP.apk`** from the GitHub Releases page and open it.
2. If Android asks, allow **Install from unknown sources** for your browser or file manager.
3. Open **MicHP** and allow the **microphone** and **notification** permissions.

(To build the APK yourself, follow `android/README.md`: Android Studio → new project → copy the files → Build APK.)

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

## 6. Good to know
- **Tested:** the Android app on a real phone, the Windows installer including the automatic VB-Cable install, sound in other apps through CABLE Output, adjustable mic volume, a screen scaling of 125% or more, and the phone's screen being off. The sound is clear with almost no noticeable delay. All of this was tested on the author's own setup, so other routers, phones and Windows versions may behave differently.
- **Clear sound, low delay:** audio is sent uncompressed (about 770 kbps), which is small for home WiFi and keeps the sound clean.
- **One phone at a time:** connect the phone you want to use; to switch phones, connect the other one.
- **Home WiFi only, not encrypted:** use it on a network you trust. Anyone on the same WiFi can make their phone show up, but nothing is used until you click **Connect** on the PC.
- If the standalone window cannot open (WebView2 missing), MicHP falls back to an Edge window automatically; that fallback has not been tried on a real PC.
