package app.clipcutter.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import org.json.JSONObject

/**
 * Runs one clipping job in the foreground, so it keeps going with the screen off or the app in the
 * background (downloads + renders can take many minutes on a phone).
 */
class ClipService : Service() {
    private var wake: PowerManager.WakeLock? = null
    private var lastNotify = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val target = intent?.getStringExtra(EXTRA_TARGET)
        val clips = intent?.getIntExtra(EXTRA_CLIPS, 2) ?: 2
        if (target == null || Job.running) {
            if (!Job.running) stopSelf()
            return START_NOT_STICKY
        }
        Job.reset(target)
        channel(this)
        val type = if (Build.VERSION.SDK_INT >= 35) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING
                   else ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
        startForeground(NOTE_ID, note("Starting…", 0, true), type)
        wake = (getSystemService(Context.POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ClipCutter:job").apply { acquire(6 * 3600 * 1000L) }

        Thread({
            var error: String? = null
            var seconds = 0L
            try {
                val raw = Py.module(this).callAttr("run", target, clips, Listener { maybeNotify() }).toString()
                val res = JSONObject(raw)
                error = res.optString("error").ifEmpty { null }
                seconds = res.optLong("seconds")
            } catch (t: Throwable) {
                error = t.message ?: t.toString()
                Job.log(t.stackTraceToString())
            }
            Job.error = error
            Job.resultSeconds = seconds
            Job.status = error ?: "Done in ${seconds / 60}m ${seconds % 60}s"
            if (error == null) Job.pct = 100.0
            Job.finishedAt = System.currentTimeMillis()
            Job.running = false
            Job.generation++
            done(error)
        }, "clipcutter-job").start()
        return START_NOT_STICKY
    }

    private fun maybeNotify() {
        val now = System.currentTimeMillis()
        if (now - lastNotify < 1000) return
        lastNotify = now
        getSystemService(NotificationManager::class.java).notify(NOTE_ID, note(Job.status, Job.pct.toInt(), false))
    }

    private fun done(error: String?) {
        wake?.let { if (it.isHeld) it.release() }
        stopForeground(STOP_FOREGROUND_REMOVE)
        val n = Notification.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle(if (error == null) "Your clips are ready" else if (Job.cancel) "Stopped" else "Couldn't make clips")
            .setContentText(error ?: Job.title.ifEmpty { "Tap to watch and share" })
            .setContentIntent(openApp())
            .setAutoCancel(true)
            .build()
        getSystemService(NotificationManager::class.java).notify(DONE_ID, n)
        stopSelf()
    }

    private fun note(text: String, pct: Int, indeterminate: Boolean): Notification =
        Notification.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle(Job.title.ifEmpty { "Making clips" })
            .setContentText(text)
            .setProgress(100, pct, indeterminate)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openApp())
            .build()

    private fun openApp() = PendingIntent.getActivity(this, 0,
        Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
        PendingIntent.FLAG_IMMUTABLE)

    override fun onDestroy() {
        wake?.let { if (it.isHeld) it.release() }
        super.onDestroy()
    }

    companion object {
        const val EXTRA_TARGET = "target"
        const val EXTRA_CLIPS = "clips"
        private const val CHANNEL = "jobs"
        private const val NOTE_ID = 1
        private const val DONE_ID = 2

        fun channel(ctx: Context) {
            val nm = ctx.getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(NotificationChannel(CHANNEL, "Clipping jobs", NotificationManager.IMPORTANCE_LOW))
        }

        fun start(ctx: Context, target: String, clips: Int) {
            ctx.startForegroundService(Intent(ctx, ClipService::class.java)
                .putExtra(EXTRA_TARGET, target).putExtra(EXTRA_CLIPS, clips))
        }
    }
}
