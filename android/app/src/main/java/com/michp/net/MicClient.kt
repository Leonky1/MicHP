package com.michp.net

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.net.ConnectivityManager
import android.os.SystemClock
import com.michp.MicRepository
import com.michp.MicStatus
import com.michp.MicUiState
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.nio.ByteBuffer
import java.nio.channels.DatagramChannel

/**
 * Flow:
 *   Connecting: send "hello" every second (broadcast) until the PC sends "accept"
 *   Online    : record the mic, send 20 ms PCM frames to the PC, and watch for "bye" from the PC
 * Everything runs on one thread. Stops when [stop] is called or the PC sends bye.
 */
class MicClient(
    private val appContext: Context,
    private val deviceId: String,
    private val deviceName: String,
    private val onFinished: () -> Unit,
) {
    @Volatile
    private var running = false

    fun start() {
        if (running) return
        running = true
        Thread({ loop() }, "michp-client").start()
    }

    fun stop() {
        running = false
    }

    private fun loop() {
        var ctrl: DatagramChannel? = null
        var pcIp: InetAddress? = null
        var session = 0L
        var endedByPc = false
        try {
            ctrl = DatagramChannel.open()
            ctrl.socket().reuseAddress = true
            ctrl.socket().broadcast = true
            ctrl.socket().bind(InetSocketAddress(Protocol.PHONE_CTRL_PORT))
            ctrl.configureBlocking(false)

            // ---- Mic Connecting.. ----
            val hello = Protocol.hello(deviceId, deviceName, Protocol.PHONE_CTRL_PORT)
            val buf = ByteBuffer.allocate(2048)
            var lastHello = 0L
            var accept: org.json.JSONObject? = null
            while (running && accept == null) {
                val now = SystemClock.elapsedRealtime()
                if (now - lastHello >= 1000) {
                    for (ip in broadcastTargets()) sendTo(ctrl, hello, ip, Protocol.DISCOVERY_PORT)
                    lastHello = now
                }
                buf.clear()
                val from = ctrl.receive(buf)
                if (from == null) {
                    Thread.sleep(20)
                    continue
                }
                val msg = Protocol.parse(buf.array(), buf.position())
                if (msg != null && msg.optString("t") == "accept") {
                    accept = msg
                    pcIp = (from as InetSocketAddress).address
                }
            }

            if (accept == null || pcIp == null) {
                // cancelled by the user before the PC connected -> tell the PC so the phone name disappears
                val bye = Protocol.bye(deviceId, 0)
                for (ip in broadcastTargets()) sendTo(ctrl, bye, ip, Protocol.DISCOVERY_PORT)
                return
            }

            // ---- Mic Online ----
            session = accept.optLong("session")
            val audioPort = accept.optInt("audio_port", Protocol.DEFAULT_AUDIO_PORT)
            val pcName = accept.optString("pc_name").ifBlank { null }
            // The timer is NOT touched here: it has been running since the mic was switched on.
            MicRepository.update { it.copy(status = MicStatus.Online, pcName = pcName, error = null) }
            endedByPc = streamAudio(ctrl, pcIp, audioPort, session)
        } catch (e: Exception) {
            MicRepository.update { it.copy(error = "Connection failed: " + (e.message ?: e.javaClass.simpleName)) }
        } finally {
            if (ctrl != null) {
                if (!endedByPc && pcIp != null && session != 0L) {
                    sendTo(ctrl, Protocol.bye(deviceId, session), pcIp, Protocol.DISCOVERY_PORT)
                }
                try { ctrl.close() } catch (_: Exception) {}
            }
            running = false
            // Mic switched off (by the user, the PC, or an error): freeze the timer at how long it ran.
            MicRepository.update { prev ->
                val frozen = prev.activeSinceMs
                    ?.let { (SystemClock.elapsedRealtime() - it).coerceAtLeast(0L) }
                    ?: prev.frozenMs
                MicUiState(status = MicStatus.Offline, error = prev.error, frozenMs = frozen)
            }
            onFinished()
        }
    }

    /** Returns true if the PC ended the session (sent bye). */
    @SuppressLint("MissingPermission")
    private fun streamAudio(ctrl: DatagramChannel, pcIp: InetAddress, audioPort: Int, session: Long): Boolean {
        val minBuf = AudioRecord.getMinBufferSize(
            Protocol.SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val bufSize = maxOf(minBuf, Protocol.FRAME_BYTES * 4)
        val rec = AudioRecord(
            MediaRecorder.AudioSource.MIC, Protocol.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufSize)
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            MicRepository.update { it.copy(error = "Could not open the microphone. Check the microphone permission.") }
            return false
        }
        val sock = DatagramSocket()
        val target = InetSocketAddress(pcIp, audioPort)
        val pcm = ByteArray(Protocol.FRAME_BYTES)
        val packet = ByteArray(Protocol.HEADER_SIZE + Protocol.FRAME_BYTES)
        val ctrlBuf = ByteBuffer.allocate(512)
        var seq = 0
        var endedByPc = false
        try {
            rec.startRecording()
            while (running) {
                if (!readFully(rec, pcm)) break
                val n = Protocol.packAudio(session, seq, pcm, Protocol.FRAME_BYTES, packet)
                try {
                    sock.send(DatagramPacket(packet, n, target))
                } catch (_: Exception) {
                    // the network dropped for a moment; carry on with the next frame
                }
                seq++
                if (seq % 2 == 0) pushLevel(Protocol.level(pcm, Protocol.FRAME_BYTES))

                ctrlBuf.clear()
                if (ctrl.receive(ctrlBuf) != null) {
                    val m = Protocol.parse(ctrlBuf.array(), ctrlBuf.position())
                    if (m != null && m.optString("t") == "bye") {
                        endedByPc = true
                        break
                    }
                }
            }
        } finally {
            try { rec.stop() } catch (_: Exception) {}
            rec.release()
            sock.close()
        }
        return endedByPc
    }

    private fun readFully(rec: AudioRecord, buf: ByteArray): Boolean {
        var off = 0
        while (off < buf.size) {
            if (!running) return false
            val n = rec.read(buf, off, buf.size - off)
            if (n < 0) return false
            off += n
        }
        return true
    }

    private fun pushLevel(level: Float) {
        MicRepository.update { it.copy(levels = it.levels.drop(1) + level) }
    }

    private fun sendTo(ch: DatagramChannel, data: ByteArray, ip: InetAddress, port: Int) {
        try {
            ch.send(ByteBuffer.wrap(data), InetSocketAddress(ip, port))
        } catch (_: Exception) {
            // ignore: UDP, it is tried again in the next cycle
        }
    }

    /** WiFi subnet broadcast address + 255.255.255.255. */
    private fun broadcastTargets(): List<InetAddress> {
        val out = mutableListOf<InetAddress>()
        try {
            val cm = appContext.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val props = cm.getLinkProperties(cm.activeNetwork)
            props?.linkAddresses?.forEach { la ->
                val a = la.address
                if (a is Inet4Address) {
                    val ip = ByteBuffer.wrap(a.address).int
                    val mask = if (la.prefixLength == 0) 0 else (-1 shl (32 - la.prefixLength))
                    val bc = ip or mask.inv()
                    out.add(InetAddress.getByAddress(ByteBuffer.allocate(4).putInt(bc).array()))
                }
            }
        } catch (_: Exception) {
        }
        out.add(InetAddress.getByAddress(byteArrayOf(-1, -1, -1, -1)))
        return out.distinct()
    }
}
