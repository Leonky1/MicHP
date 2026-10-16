package com.michp

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

enum class MicStatus { Offline, Connecting, Online }

const val LEVEL_BARS = 28

data class MicUiState(
    val status: MicStatus = MicStatus.Offline,
    val pcName: String? = null,
    val levels: List<Float> = List(LEVEL_BARS) { 0f },
    val error: String? = null,
    /**
     * SystemClock.elapsedRealtime() at the moment the mic was switched on (button pressed),
     * whether it is still Connecting or already Online. null while the mic is off.
     */
    val activeSinceMs: Long? = null,
    /**
     * How long the mic was on during the last session, in ms. Set when the mic is switched off
     * and shown frozen until the next start. null if the mic has not been used yet.
     */
    val frozenMs: Long? = null,
)

/**
 * The single source of status for the UI. Written from the network/audio threads,
 * read by Compose (mutableStateOf is safe to write from other threads).
 */
object MicRepository {
    var state by mutableStateOf(MicUiState())
        private set

    @Synchronized
    fun update(block: (MicUiState) -> MicUiState) {
        state = block(state)
    }
}
