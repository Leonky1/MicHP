# MicHP — Android app (Checkpoint 3)

> **Honest status:** this Kotlin code has **never been compiled or run**.
> The sandbox it was written in has no Android SDK and cannot download dependencies.
> There may be 1–3 small compile errors (imports, API versions). Send the error messages from
> Android Studio and they will be fixed. [Medium confidence] the logic is right because it follows
> the protocol that is already tested on the PC side; the UI and audio need a test on a real phone.

## How to install (about 10 minutes)

1. Install **Android Studio** (latest version).
2. `New Project` → **Empty Activity** (the Compose / Material3 one).
   - Name: `MicHP`
   - **Package name: `com.michp`** (must be the same)
   - Minimum SDK: **API 26** or higher.
3. Once the project is created, **overwrite/copy** the contents of this folder into the project:
   - `app/src/main/AndroidManifest.xml` → overwrite the default manifest
   - `app/src/main/res/*` → copy into the project's `res` folder (this is the app logo; overwrite `mipmap-anydpi-v26/ic_launcher*.xml`)
   - `app/src/main/java/com/michp/*` → copy everything (delete the default `MainActivity.kt` and the default `ui/theme` folder if they cause errors, they are not used)
4. `Build > Make Project`. If there are red errors, copy the message to me.
5. Plug in the phone (USB debugging on) → **Run** button. Or `Build > Build APK(s)` and send the APK to the phone.

## Already have an old project (package `com.wifimic`)?

The package name changed to `com.michp`. In Android Studio: right-click the package `com.wifimic` →
**Refactor → Rename** → `michp`; then in `app/build.gradle(.kts)` change `namespace` and
`applicationId` to `com.michp`. Because the `applicationId` is different, Android treats this as a
new app: uninstall the old app from the phone and install the new one. The easiest alternative: create a
new project with the package `com.michp` (steps above) and copy the files in.

## Using it

1. On the PC: run MicHP (see the main README).
2. On the phone: close any VPN, make sure you are on the same WiFi as the PC, open MicHP → tap **Turn On Mic**
   (allow the microphone & notifications) → yellow status **Mic Connecting..**
   The **Active for 00:00:00** timer starts counting right away, even before the PC connects.
3. The phone's name shows up on the PC → click **Connect** → the phone turns green **Mic Online**.
4. Tap **Turn Off Mic** (or **Cancel** while still connecting) → the timer freezes and shows
   **Last session HH:MM:SS** until the next start.

## Files

| File | Purpose |
|---|---|
| `net/Protocol.kt` | message format & audio packet (same as PROTOCOL.md) |
| `net/MicClient.kt` | broadcast hello → wait for accept → record & send audio; freezes the timer when it ends |
| `MicService.kt` | foreground service (the mic keeps running with the screen off); starts the timer |
| `MicRepository.kt` | status for the UI (including `activeSinceMs` / `frozenMs`) |
| `ui/MicHPScreen.kt` | UI design 1 (3 statuses + timer) |
| `MainActivity.kt` | permissions + button |
| `DeviceInfo.kt` | phone ID & name |
