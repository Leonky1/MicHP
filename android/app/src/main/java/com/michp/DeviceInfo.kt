package com.michp

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.provider.Settings
import java.util.UUID

object DeviceInfo {
    /** Unique phone ID, created once and then saved. */
    fun id(ctx: Context): String {
        val prefs = ctx.getSharedPreferences("michp", Context.MODE_PRIVATE)
        val saved = prefs.getString("id", null)
        if (saved != null) return saved
        val fresh = UUID.randomUUID().toString()
        prefs.edit().putString("id", fresh).apply()
        return fresh
    }

    /** The name shown in the PC software (device name from Settings, or the phone model). */
    fun name(ctx: Context): String {
        val fromSettings: String? = try {
            Settings.Global.getString(ctx.contentResolver, "device_name")
        } catch (e: Exception) {
            null
        }
        val raw = (fromSettings ?: Build.MODEL ?: "").trim()
        return if (raw.isEmpty()) "HP" else raw.take(40)
    }

    fun isOnWifi(ctx: Context): Boolean {
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
    }
}
