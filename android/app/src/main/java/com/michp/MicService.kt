package com.michp

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.michp.net.MicClient

/**
 * Foreground service so the mic keeps running with the screen off / app in the background.
 * Android requires a notification while the mic is in use.
 */
class MicService : Service() {
    private var client: MicClient? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            val c = client
            if (c != null) c.stop() else stopSelf()
        } else {
            startClient()
        }
        return START_NOT_STICKY
    }

    private fun startClient() {
        if (client != null) return
        startAsForeground()
        acquireLocks()
        // The timer starts the moment the mic is switched on, even while still Connecting.
        MicRepository.update {
            MicUiState(status = MicStatus.Connecting,
                activeSinceMs = SystemClock.elapsedRealtime())
        }
        val c = MicClient(applicationContext, DeviceInfo.id(this), DeviceInfo.name(this)) {
            client = null
            stopSelf()
        }
        client = c
        c.start()
    }

    private fun startAsForeground() {
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "MicHP", NotificationManager.IMPORTANCE_LOW))
        }
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val stop = PendingIntent.getService(
            this, 1, Intent(this, MicService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE)
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("MicHP is active")
            .setContentText("Your phone is working as a PC mic")
            .setContentIntent(open)
            .addAction(0, "Stop", stop)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= 30) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIF_ID, notification)
        }
    }

    private fun acquireLocks() {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "michp:mic").apply {
            setReferenceCounted(false)
            acquire() // no timeout; released in onDestroy when the mic stops
        }
        val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val mode = if (Build.VERSION.SDK_INT >= 29) {
            WifiManager.WIFI_MODE_FULL_LOW_LATENCY
        } else {
            @Suppress("DEPRECATION")
            WifiManager.WIFI_MODE_FULL_HIGH_PERF
        }
        wifiLock = wm.createWifiLock(mode, "michp:wifi").apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    override fun onDestroy() {
        client?.stop()
        client = null
        try { wakeLock?.let { if (it.isHeld) it.release() } } catch (_: Exception) {}
        try { wifiLock?.let { if (it.isHeld) it.release() } } catch (_: Exception) {}
        super.onDestroy()
    }

    companion object {
        const val ACTION_START = "com.michp.START"
        const val ACTION_STOP = "com.michp.STOP"
        private const val CHANNEL_ID = "michp"
        private const val NOTIF_ID = 1
    }
}
