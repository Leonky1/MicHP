package com.michp.net

import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.log10
import kotlin.math.sqrt

/** MicHP protocol v1 (see PROTOCOL.md). Must match the PC side exactly. */
object Protocol {
    const val VERSION = 1
    const val DISCOVERY_PORT = 48100      // PC listens
    const val PHONE_CTRL_PORT = 48102     // phone listens
    const val DEFAULT_AUDIO_PORT = 48101

    const val SAMPLE_RATE = 48000
    const val FRAME_SAMPLES = 960         // 20 ms
    const val FRAME_BYTES = FRAME_SAMPLES * 2
    const val HEADER_SIZE = 12
    private const val TYPE_AUDIO = 1

    fun hello(id: String, name: String, ctrlPort: Int): ByteArray =
        JSONObject()
            .put("t", "hello").put("v", VERSION)
            .put("id", id).put("name", name).put("ctrl_port", ctrlPort)
            .toString().toByteArray(Charsets.UTF_8)

    fun bye(id: String, session: Long): ByteArray =
        JSONObject()
            .put("t", "bye").put("v", VERSION)
            .put("id", id).put("session", session)
            .toString().toByteArray(Charsets.UTF_8)

    /** Returns the valid control message, or null. */
    fun parse(data: ByteArray, len: Int): JSONObject? {
        if (len <= 0 || data[0] != '{'.code.toByte()) return null
        return try {
            val o = JSONObject(String(data, 0, len, Charsets.UTF_8))
            if (o.optInt("v") == VERSION && o.optString("t").isNotEmpty()) o else null
        } catch (e: Exception) {
            null
        }
    }

    /** Fills [out] with the 12-byte header + PCM. Returns the number of bytes to send. */
    fun packAudio(session: Long, seq: Int, pcm: ByteArray, len: Int, out: ByteArray): Int {
        val bb = ByteBuffer.wrap(out).order(ByteOrder.LITTLE_ENDIAN)
        bb.put('W'.code.toByte())
        bb.put('M'.code.toByte())
        bb.put(VERSION.toByte())
        bb.put(TYPE_AUDIO.toByte())
        bb.putInt(session.toInt())   // u32 disimpan sebagai pola bit 32-bit
        bb.putInt(seq)
        bb.put(pcm, 0, len)
        return HEADER_SIZE + len
    }

    /** Sound level 0..1 from RMS (dBFS scale: -60 dB = 0, 0 dB = 1). Same as the PC side. */
    fun level(pcm: ByteArray, len: Int): Float {
        val n = len / 2
        if (n == 0) return 0f
        var acc = 0.0
        var i = 0
        while (i + 1 < len) {
            val s = (pcm[i].toInt() and 0xFF) or (pcm[i + 1].toInt() shl 8)  // little-endian, bertanda
            acc += (s * s).toDouble()
            i += 2
        }
        val rms = sqrt(acc / n)
        if (rms <= 0.0) return 0f
        val db = 20.0 * log10(rms / 32768.0)
        return ((db + 60.0) / 60.0).coerceIn(0.0, 1.0).toFloat()
    }
}
