# MicHP Protocol v1

Everything runs over UDP on the local network (home WiFi). There is no server on the internet.

| Port  | Who listens | Contents |
|-------|-------------|----------|
| 48100 | PC | `hello` and `bye` from the phone |
| 48101 | PC | audio packets from the phone |
| 48102 | Phone | `accept` and `bye` from the PC (the phone may announce another port through `ctrl_port`) |

## Flow (matches the design)

1. The phone taps **Mic Offline** -> shows **Mic Connecting..**. The phone sends `hello` every second
   (broadcast to `255.255.255.255:48100`, or to the subnet broadcast address).
2. The PC receives `hello` -> the phone's name shows up + a **Connect** button.
3. The user clicks **Connect** -> the PC sends `accept` (unicast) to the phone.
4. The phone stops sending `hello`, shows **Mic Online**, and starts sending audio to `PC_IP:audio_port`.
   The PC's IP is taken from the sender address of `accept`.
5. Ending: either side sends `bye`. If no audio arrives for 3 seconds, the PC treats the connection as lost.

If `accept` gets lost (UDP), the phone keeps sending `hello`; a PC that is already "connected" to that phone
re-sends `accept` with the same `session`.

## Timers (no protocol involvement)

Both timers are counted locally with a monotonic clock. **Nothing about them goes over the wire.**

- **PC:** connected time, counted from the first audio packet. If the connection ends *on its own*
  (audio timeout, or the phone sent `bye`) the time is frozen and kept on screen until the next
  Connect. Clicking **Disconnect** on the PC clears it.
- **Phone:** starts when the mic is switched on (**Turn On Mic**), even while still Connecting. It freezes
  when the mic is switched off and shows the last session time until the next start.

## Control messages (JSON, one UDP packet each)

```json
{"t":"hello","v":1,"id":"<unique phone id>","name":"My Phone","ctrl_port":48102}
{"t":"accept","v":1,"session":123456,"audio_port":48101,"rate":48000,"ch":1,"fmt":"s16le","frame":960}
{"t":"bye","v":1,"id":"<sender id>","session":123456}
```

## Audio packet (binary, little-endian)

```
offset  size  contents
0       2     magic "WM"
2       1     version (1)
3       1     type (1 = audio)
4       4     session (u32, from accept)
8       4     seq (u32, +1 per frame, wraps at 2^32)
12      ...   PCM signed 16-bit mono 48000 Hz, 960 samples (20 ms) = 1920 bytes
```

The PC rejects packets with a different session, or whose sender IP is not the connected phone.
`seq` is used to count lost/late packets.

## Why raw PCM and not Opus?

Simple and low latency. Bandwidth is about 770 kbps, which is fine on home WiFi.
Opus can be added later if saving data matters.
