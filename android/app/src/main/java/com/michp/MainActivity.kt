package com.michp

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import com.michp.ui.MicHPScreen

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) {
        // The notification permission may be denied; only the microphone is required.
        if (granted(Manifest.permission.RECORD_AUDIO)) {
            startMic()
        } else {
            toast("Microphone permission is needed so the phone can work as a mic")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val deviceName = DeviceInfo.name(this)
        setContent {
            MicHPScreen(
                state = MicRepository.state,
                deviceName = deviceName,
                onToggle = { onToggle() },
            )
        }
    }

    private fun onToggle() {
        if (MicRepository.state.status != MicStatus.Offline) {
            stopMic()
            return
        }
        if (!DeviceInfo.isOnWifi(this)) {
            toast("Connect your phone to the same WiFi as the PC first")
            return
        }
        val need = mutableListOf<String>()
        if (!granted(Manifest.permission.RECORD_AUDIO)) need.add(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33 && !granted(Manifest.permission.POST_NOTIFICATIONS)) {
            need.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (need.isEmpty()) startMic() else permissionLauncher.launch(need.toTypedArray())
    }

    private fun startMic() {
        MicRepository.update { it.copy(error = null) }
        ContextCompat.startForegroundService(
            this, Intent(this, MicService::class.java).setAction(MicService.ACTION_START))
    }

    private fun stopMic() {
        startService(Intent(this, MicService::class.java).setAction(MicService.ACTION_STOP))
    }

    private fun granted(permission: String): Boolean =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
}
