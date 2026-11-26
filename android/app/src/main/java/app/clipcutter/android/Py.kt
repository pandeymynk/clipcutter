package app.clipcutter.android

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File

/** Starts the embedded Python once and points the shared pipeline at the app's folders and tools. */
object Py {
    @Volatile var doctor: String = ""
        private set
    private var ready = false

    @Synchronized
    fun module(ctx: Context): PyObject {
        val app = ctx.applicationContext
        if (!Python.isStarted()) Python.start(AndroidPlatform(app))
        val m = Python.getInstance().getModule("android_app")
        if (!ready) {
            val res = File(app.filesDir, "res")
            copyAssets(app, "fonts", File(res, "fonts"))
            doctor = m.callAttr("setup", app.filesDir.absolutePath,
                app.applicationInfo.nativeLibraryDir, res.absolutePath).toString()
            ready = true
        }
        return m
    }

    private fun copyAssets(ctx: Context, dir: String, dest: File) {
        val names = ctx.assets.list(dir) ?: return
        dest.mkdirs()
        for (name in names) {
            val out = File(dest, name)
            ctx.assets.open("$dir/$name").use { input ->
                val size = input.available().toLong()
                if (out.exists() && out.length() == size) return@use
                out.outputStream().use { input.copyTo(it) }
            }
        }
    }
}
