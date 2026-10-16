package com.michp.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import android.os.SystemClock
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.michp.MicStatus
import com.michp.MicUiState
import kotlinx.coroutines.delay

private val Bg = Color(0xFF050A1E)
private val Accent = Color(0xFF2F6BF2)
private val Green = Color(0xFF22C55E)
private val Yellow = Color(0xFFF5B301)
private val Grey = Color(0xFF4B5563)
private val TextMain = Color(0xFFF2F5FF)
private val TextMuted = Color(0xFF9AA7C7)
private val GlassFill = Color(0x0DFFFFFF)     // 5%
private val GlassBorder = Color(0x17FFFFFF)   // 9%

@Composable
fun MicHPScreen(state: MicUiState, deviceName: String, onToggle: () -> Unit) {
    val color by animateColorAsState(
        when (state.status) {
            MicStatus.Offline -> Grey
            MicStatus.Connecting -> Yellow
            MicStatus.Online -> Green
        }, label = "statusColor")

    val title = when (state.status) {
        MicStatus.Offline -> "Mic Offline"
        MicStatus.Connecting -> "Mic Connecting.."
        MicStatus.Online -> "Mic Online"
    }
    val subtitle = when (state.status) {
        MicStatus.Offline -> "Tap the button to start"
        MicStatus.Connecting -> "Waiting for the PC to press Connect"
        MicStatus.Online -> "Connected to " + (state.pcName ?: "PC")
    }
    val action = when (state.status) {
        MicStatus.Offline -> "Turn On Mic"
        MicStatus.Connecting -> "Cancel"
        MicStatus.Online -> "Turn Off Mic"
    }

    // Timer: runs from the moment the mic is switched on (Connecting or Online alike).
    // When the mic is switched off it freezes at how long it last ran.
    val since = state.activeSinceMs
    val frozen = state.frozenMs
    var nowMs by remember { mutableStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(since) {
        while (since != null) {
            nowMs = SystemClock.elapsedRealtime()
            delay(250)
        }
    }
    // Always present (a space when there is nothing to show) so the layout does not shift when the status changes.
    val activeFor = when {
        since != null -> "Active for " + formatDuration((nowMs - since).coerceAtLeast(0L) / 1000)
        frozen != null -> "Last session " + formatDuration(frozen / 1000)
        else -> " "
    }

    Box(
        Modifier
            .fillMaxSize()
            .background(Bg)
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(horizontal = 20.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("MicHP", color = TextMain, fontSize = 20.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth())
            Text(deviceName, color = TextMuted, fontSize = 13.sp, modifier = Modifier.fillMaxWidth())

            Spacer(Modifier.weight(1f))

            // status card (glass)
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(24.dp))
                    .background(GlassFill)
                    .border(1.dp, GlassBorder, RoundedCornerShape(24.dp))
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                StatusDot(color, pulsing = state.status == MicStatus.Connecting)
                Spacer(Modifier.height(16.dp))
                Text(title, color = color, fontSize = 28.sp, fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center)
                Spacer(Modifier.height(6.dp))
                Text(subtitle, color = TextMuted, fontSize = 14.sp, textAlign = TextAlign.Center)
                Spacer(Modifier.height(4.dp))
                Text(activeFor, color = TextMain, fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center)
                Spacer(Modifier.height(24.dp))
                LevelBars(state.levels, color, active = state.status == MicStatus.Online)
            }

            if (state.error != null) {
                Spacer(Modifier.height(12.dp))
                Text(state.error, color = Color(0xFFFF8A80), fontSize = 13.sp, textAlign = TextAlign.Center)
            }

            // button right below the card (not stuck to the bottom of the screen)
            Spacer(Modifier.height(20.dp))

            Box(
                Modifier
                    .fillMaxWidth()
                    .height(56.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .background(if (state.status == MicStatus.Offline) Accent else GlassFill)
                    .border(1.dp,
                        if (state.status == MicStatus.Offline) Accent else GlassBorder,
                        RoundedCornerShape(18.dp))
                    .clickable(role = Role.Button, onClick = onToggle),
                contentAlignment = Alignment.Center,
            ) {
                Text(action, color = TextMain, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.weight(1f))
        }
    }
}

/** 3725 seconds -> "01:02:05" */
fun formatDuration(totalSeconds: Long): String {
    val h = totalSeconds / 3600
    val m = (totalSeconds / 60) % 60
    val s = totalSeconds % 60
    return "%02d:%02d:%02d".format(h, m, s)
}

@Composable
private fun StatusDot(color: Color, pulsing: Boolean) {
    val t = rememberInfiniteTransition(label = "pulse")
    val scale by t.animateFloat(
        initialValue = 1f, targetValue = if (pulsing) 1.5f else 1f,
        animationSpec = infiniteRepeatable(tween(900), RepeatMode.Reverse), label = "scale")
    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(72.dp)) {
        Box(Modifier.size(40.dp * scale).background(color.copy(alpha = 0.22f), CircleShape))
        Box(Modifier.size(24.dp).background(color, CircleShape))
    }
}

@Composable
private fun LevelBars(levels: List<Float>, color: Color, active: Boolean) {
    Canvas(Modifier.fillMaxWidth().height(48.dp)) {
        val n = levels.size
        val gap = 4.dp.toPx()
        val w = (size.width - gap * (n - 1)) / n
        for (i in 0 until n) {
            val v = if (active) levels[i] else 0f
            val h = (size.height * v).coerceAtLeast(4.dp.toPx())
            drawRoundRect(
                color = if (active && v > 0.02f) color else Color(0x22FFFFFF),
                topLeft = Offset(i * (w + gap), (size.height - h) / 2f),
                size = Size(w, h),
                cornerRadius = CornerRadius(w / 2f, w / 2f),
            )
        }
    }
}
