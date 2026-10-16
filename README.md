<p align="center">
  <img src="branding/logo-512.png" width="120" alt="MicHP logo">
</p>

<h1 align="center">MicHP</h1>

<p align="center">
  Use your Android phone as a wireless microphone for your Windows PC, over your home WiFi.<br>
  No internet, no account, no cables.
</p>

> **Status: early beta.** The PC side is covered by automated tests, but it has **not yet been tested on real
> hardware** (Windows install, VB-Cable, real router) and the Android app has **never been compiled**.
> See [Known limitations](#known-limitations). Bug reports are very welcome!

## What it does

Your phone's microphone becomes a microphone on your PC. Pick it in Discord, OBS, Zoom, games, or any app that
lets you choose a microphone.

```
 Phone mic ──(WiFi, UDP)──▶ MicHP on PC ──▶ virtual mic (VB-Cable) ──▶ Discord / OBS / Zoom
```

## Download and install (Windows)

1. Go to the **[Releases page](../../releases/latest)** and download **`MicHP-Setup.exe`**.
2. Double-click it and click **Install**.
   - It also installs **VB-Cable** (a free virtual microphone by VB-Audio) if you don't have it yet.
     Windows will ask for Administrator permission, and at the end you should **restart the PC**.
3. Open **MicHP** from the Start Menu or Desktop.
4. When Windows Firewall asks, allow it on **Private networks**.

## Install the phone app (Android)

> The ready-made APK is not available yet. For now, build it with Android Studio:
> follow **[android/README.md](android/README.md)** (about 10 minutes).
> Once an APK is attached to a Release, you will be able to just download and install it.

## How to use

1. PC: open **MicHP**. In Discord/OBS/Zoom, choose **CABLE Output** as the microphone.
2. Phone: open **MicHP** → tap **Turn On Mic** (yellow: *Mic Connecting..*).
3. PC: your phone's name appears → click **Connect**. The phone turns green: *Mic Online*.
4. Talk. The sound bar on the PC moves. Turn on **Hear yourself** to test (use a headset to avoid echo).

Both devices must be on the **same WiFi network** (not a guest network, VPN off).

More detail, a first-test checklist and troubleshooting: **[GUIDE.md](GUIDE.md)**.

## Known limitations

- Home network only. The audio is **not encrypted**; anyone on the same WiFi could try to connect
  (you still have to click **Connect** on the PC).
- Raw audio, about 770 kbps. One phone at a time.
- **Not yet tested on real devices:** the Android app (never compiled), the Windows installer and automatic
  VB-Cable install, broadcast on a real router, latency (expected 60–150 ms).
- Windows and Android only.

## For developers

```
cd pc
python -m unittest discover -s tests -t . -v     # 63 tests
python -m michp_pc --no-audio                    # run the UI without audio output
python -m michp_pc.fake_phone --seconds 10       # fake phone, in another terminal
```

- [PROTOCOL.md](PROTOCOL.md): how the phone and PC talk to each other
- [docs/BLUEPRINT.md](docs/BLUEPRINT.md): design and architecture
- [AGENTS.md](AGENTS.md): project rules and conventions
- [pc/README.md](pc/README.md): running from source on Windows
- [PROGRESS.md](PROGRESS.md): status per checkpoint

**Releasing a new Windows installer:** push a tag, e.g. `git tag v1.0.0 && git push origin v1.0.0`.
The *Release* workflow builds `MicHP-Setup.exe` and attaches it to a GitHub Release automatically.

## License

[MIT](LICENSE). VB-Cable is a separate product by VB-Audio and is downloaded from their website, not
bundled in this repository; please respect its license.
