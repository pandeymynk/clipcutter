package app.clipcutter.android

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.net.ConnectivityManager
import android.net.NetworkInfo
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val ui = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private val thumbs = HashMap<String, Bitmap?>()
    private var shownGeneration = -1

    private lateinit var url: EditText
    private lateinit var clips: Spinner
    private lateinit var jobCard: View
    private lateinit var jobTitle: TextView
    private lateinit var jobStatus: TextView
    private lateinit var jobTime: TextView
    private lateinit var jobBar: ProgressBar
    private lateinit var list: LinearLayout
    private lateinit var empty: TextView

    private val tick = object : Runnable {
        override fun run() {
            renderJob()
            ui.postDelayed(this, 500)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        url = findViewById(R.id.url)
        clips = findViewById(R.id.clips)
        jobCard = findViewById(R.id.jobCard)
        jobTitle = findViewById(R.id.jobTitle)
        jobStatus = findViewById(R.id.jobStatus)
        jobTime = findViewById(R.id.jobTime)
        jobBar = findViewById(R.id.jobBar)
        list = findViewById(R.id.list)
        empty = findViewById(R.id.empty)

        clips.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf(1, 2, 3, 4, 5))
        clips.setSelection(1)
        findViewById<Button>(R.id.start).setOnClickListener { startFromUrl() }
        url.setOnEditorActionListener { _, id, _ -> if (id == EditorInfo.IME_ACTION_GO) { startFromUrl(); true } else false }
        findViewById<Button>(R.id.pick).setOnClickListener {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("video/*"), PICK)
        }
        findViewById<Button>(R.id.stop).setOnClickListener {
            if (Job.running) { Job.cancel = true; Job.status = "Stopping after this step…" }
        }
        findViewById<Button>(R.id.log).setOnClickListener { showLog() }
        findViewById<Button>(R.id.ai).setOnClickListener { aiDialog() }
        findViewById<Button>(R.id.about).setOnClickListener { about() }

        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        handleShare(intent)
        io.execute { Py.module(this) }   // warm up Python (first start unpacks it: a few seconds)
        // Automation hook for tests: adb shell am start -n app.clipcutter.android/.MainActivity --es autostart <url>
        intent.getStringExtra("autostart")?.let { url.setText(it); startFromUrl(intent.getIntExtra("clips", 1)) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShare(intent)
        intent.getStringExtra("autostart")?.let { url.setText(it); startFromUrl(intent.getIntExtra("clips", 1)) }
    }

    override fun onResume() {
        super.onResume()
        ui.post(tick)
    }

    override fun onPause() {
        ui.removeCallbacks(tick)
        super.onPause()
    }

    private fun handleShare(i: Intent?) {
        if (i?.action != Intent.ACTION_SEND) return
        val text = i.getStringExtra(Intent.EXTRA_TEXT) ?: return
        Regex("https?://\\S+").find(text)?.let { url.setText(it.value) }
    }

    private fun startFromUrl(count: Int? = null) {
        val target = url.text.toString().trim()
        if (!target.startsWith("http")) {
            toast("Paste a video link first (or pick a video)")
            return
        }
        start(target, count)
    }

    /** null when the app can reach the internet, else what to tell the user. */
    private fun networkProblem(): String? {
        val cm = getSystemService(ConnectivityManager::class.java)
        @Suppress("DEPRECATION")
        val info = cm.activeNetworkInfo
        @Suppress("DEPRECATION")
        return when {
            info?.detailedState == NetworkInfo.DetailedState.BLOCKED ->
                "Internet is blocked for ClipCutter. Settings → Apps → ClipCutter → allow Wi-Fi and Mobile data " +
                "(Xiaomi/POCO: Restrict data usage), and turn off Data Saver for it."
            cm.activeNetwork == null || info?.isConnected != true -> "No internet connection. Turn on Wi-Fi and try again."
            else -> null
        }
    }

    private fun start(target: String, count: Int? = null) {
        if (Job.running) { toast("Already making clips. Stop that job first."); return }
        if (target.startsWith("http")) networkProblem()?.let {
            AlertDialog.Builder(this).setTitle("Can't download").setMessage(it).setPositiveButton("OK", null).show()
            return
        }
        ClipService.start(this, target, count ?: (clips.selectedItem as Int))
        jobCard.visibility = View.VISIBLE
        Job.status = "Starting…"
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri = data?.data ?: return
        if (requestCode != PICK || resultCode != RESULT_OK) return
        jobCard.visibility = View.VISIBLE
        jobStatus.text = "Copying the video into the app…"
        io.execute {
            val f = try { importVideo(uri) } catch (e: Exception) { null }
            ui.post { if (f == null) toast("Couldn't read that video") else start(f.absolutePath) }
        }
    }

    /** ffmpeg needs a real file path, so a picked video is copied into the app's own folder first. */
    private fun importVideo(uri: Uri): File {
        var name = "video.mp4"
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
            if (it.moveToFirst()) name = it.getString(0) ?: name
        }
        name = name.replace(Regex("[^A-Za-z0-9._ -]"), "_")
        val dir = File(filesDir, "imports").apply { mkdirs() }
        dir.listFiles()?.forEach { it.delete() }   // keep only the latest import (videos are big)
        val out = File(dir, name)
        contentResolver.openInputStream(uri)!!.use { input -> out.outputStream().use { input.copyTo(it, 1 shl 20) } }
        return out
    }

    private fun renderJob() {
        val active = Job.running || Job.finishedAt > 0
        jobCard.visibility = if (active) View.VISIBLE else jobCard.visibility
        if (active) {
            jobTitle.text = Job.title.ifEmpty { Job.target.substringAfterLast('/') }
            jobStatus.text = Job.status
            jobBar.progress = (Job.pct * 10).toInt()
            jobBar.isIndeterminate = Job.running && Job.pct <= 0.0
            val end = if (Job.running) System.currentTimeMillis() else Job.finishedAt
            val s = ((end - Job.startedAt) / 1000).coerceAtLeast(0)
            jobTime.text = "%d:%02d".format(s / 60, s % 60)
            findViewById<Button>(R.id.stop).visibility = if (Job.running) View.VISIBLE else View.GONE
        }
        if (shownGeneration != Job.generation || (Job.running && System.currentTimeMillis() % 5000 < 500)) {
            shownGeneration = Job.generation
            loadClips()
        }
    }

    private fun loadClips() = io.execute {
        val raw = try { Py.module(this).callAttr("list_clips").toString() } catch (e: Exception) { "[]" }
        ui.post { showClips(JSONArray(raw)) }
    }

    private fun showClips(videos: JSONArray) {
        list.removeAllViews()
        var n = 0
        for (v in 0 until videos.length()) {
            val arr = videos.getJSONObject(v).getJSONArray("clips")
            for (c in 0 until arr.length()) { list.addView(clipCard(arr.getJSONObject(c))); n++ }
        }
        empty.visibility = if (n == 0) View.VISIBLE else View.GONE
    }

    private fun clipCard(rec: JSONObject): View {
        val v = layoutInflater.inflate(R.layout.item_clip, list, false)
        val file = File(rec.getString("path"))
        val caption = rec.optString("post_caption")
        val title = rec.optString("title")
        v.findViewById<TextView>(R.id.hook).text = rec.optString("hook")
        val len = (rec.optDouble("end") - rec.optDouble("start")).toInt()
        v.findViewById<TextView>(R.id.meta).text = "virality ${rec.optInt("virality")} · ${len}s · ${rec.optString("source_title").take(40)}"
        v.findViewById<TextView>(R.id.caption).text = listOf(title, caption).filter { it.isNotBlank() }.joinToString("\n")
        val thumb = v.findViewById<ImageView>(R.id.thumb)
        loadThumb(file, thumb)
        thumb.setOnClickListener { play(file) }
        v.findViewById<Button>(R.id.share).setOnClickListener { share(file, caption) }
        v.findViewById<Button>(R.id.save).setOnClickListener { saveToGallery(file) }
        v.findViewById<Button>(R.id.copy).setOnClickListener { copy("$title\n\n$caption") }
        v.findViewById<Button>(R.id.edit).setOnClickListener { editDialog(rec) }
        return v
    }

    private fun clipWords(rec: JSONObject): String {
        val words = rec.optJSONArray("words")
        if (words != null && words.length() > 0)
            return (0 until words.length()).joinToString(" ") { words.getJSONObject(it).optString("w") }
        return rec.optString("transcript").trim().split(Regex("\\s+")).joinToString(" ")
    }

    /** Edit title / post caption (saved as text) or the hook / on-video captions (re-renders the clip). */
    private fun editDialog(rec: JSONObject) {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(pad, pad / 2, pad, 0) }
        fun field(label: String, value: String, lines: Int, hint: String? = null): EditText {
            box.addView(TextView(this).apply {
                text = label; setTextColor(getColor(R.color.muted)); textSize = 12f; setPadding(0, pad / 2, 0, 0)
            })
            val e = EditText(this).apply {
                setText(value); textSize = 15f
                if (lines > 1) { minLines = 2; maxLines = lines; isSingleLine = false } else isSingleLine = true
            }
            box.addView(e)
            hint?.let { box.addView(TextView(this).apply { text = it; setTextColor(getColor(R.color.muted)); textSize = 11f }) }
            return e
        }
        val oldHook = rec.optString("hook")
        val oldWords = clipWords(rec)
        val hook = field("Hook (big text on the video)", oldHook, 1)
        val words = field("Captions on the video", oldWords, 6,
            "Fix wrong words. Same number of words keeps the timing; more or fewer are spread over the clip.")
        val title = field("Title", rec.optString("title"), 2)
        val caption = field("Post caption + hashtags", rec.optString("post_caption"), 5,
            "Title and caption save instantly. A new hook or captions re-render the video (about 10-30 s).")
        AlertDialog.Builder(this).setTitle("Edit clip")
            .setView(ScrollView(this).apply { addView(box) })
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                val newHook = hook.text.toString().trim().takeIf { it.isNotEmpty() && it != oldHook.trim() }
                val newWords = words.text.toString().trim().split(Regex("\\s+")).joinToString(" ")
                    .takeIf { it != oldWords }
                saveEdit(rec.getString("path"), title.text.toString(), caption.text.toString(), newHook, newWords)
            }.show()
    }

    private fun saveEdit(path: String, title: String, caption: String, hook: String?, words: String?) {
        val redo = hook != null || words != null
        if (redo && Job.running) { toast("Wait for the current job to finish, then edit the hook or captions."); return }
        val wait = if (!redo) null else AlertDialog.Builder(this).setTitle("Re-rendering clip…")
            .setView(ProgressBar(this).apply { isIndeterminate = true; setPadding(0, 40, 0, 40) })
            .setCancelable(false).show()
        io.execute {
            val r = try {
                JSONObject(Py.module(this).callAttr("edit_clip", path, title, caption, hook, words).toString())
            } catch (e: Exception) { JSONObject().put("ok", false).put("error", e.message) }
            ui.post {
                wait?.dismiss()
                toast(if (r.optBoolean("ok")) (if (redo) "Clip re-rendered" else "Saved") else r.optString("error"))
                loadClips()
            }
        }
    }

    private fun loadThumb(file: File, view: ImageView) {
        val key = file.absolutePath + file.lastModified()
        if (thumbs.containsKey(key)) { view.setImageBitmap(thumbs[key]); return }
        io.execute {
            val bmp = try {
                MediaMetadataRetriever().run {
                    setDataSource(file.absolutePath)
                    val b = getScaledFrameAtTime(4_000_000, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, 270, 480)
                    release(); b
                }
            } catch (e: Exception) { null }
            ui.post { thumbs[key] = bmp; view.setImageBitmap(bmp) }
        }
    }

    private fun uriFor(file: File): Uri = FileProvider.getUriForFile(this, "$packageName.files", file)

    private fun play(file: File) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uriFor(file), "video/mp4")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        } catch (e: Exception) { toast("No video player found") }
    }

    private fun share(file: File, caption: String) {
        copy(caption, quiet = true)   // Instagram/TikTok drop shared text: the caption is on the clipboard to paste
        val uri = uriFor(file)
        val send = Intent(Intent.ACTION_SEND).setType("video/mp4")
            .putExtra(Intent.EXTRA_STREAM, uri)
            .putExtra(Intent.EXTRA_TEXT, caption)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        send.clipData = ClipData.newRawUri("clip", uri)
        startActivity(Intent.createChooser(send, "Post clip (caption copied)"))
    }

    private fun saveToGallery(file: File) = io.execute {
        val ok = try {
            val values = ContentValues().apply {
                put(MediaStore.Video.Media.DISPLAY_NAME, "ClipCutter_${file.parentFile?.name}_${file.name}")
                put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
                put(MediaStore.Video.Media.RELATIVE_PATH, Environment.DIRECTORY_MOVIES + "/ClipCutter")
                put(MediaStore.Video.Media.IS_PENDING, 1)
            }
            val uri = contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values)!!
            contentResolver.openOutputStream(uri)!!.use { out -> file.inputStream().use { it.copyTo(out) } }
            values.clear(); values.put(MediaStore.Video.Media.IS_PENDING, 0)
            contentResolver.update(uri, values, null, null)
            true
        } catch (e: Exception) { false }
        ui.post { toast(if (ok) "Saved to Movies/ClipCutter" else "Couldn't save the clip") }
    }

    private fun copy(text: String, quiet: Boolean = false) {
        getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("caption", text))
        if (!quiet) toast("Copied")
    }

    private fun showLog() {
        val tv = TextView(this).apply {
            text = Job.logText().ifEmpty { "No log yet." }
            setTextIsSelectable(true); textSize = 11f; setPadding(32, 24, 32, 24)
        }
        AlertDialog.Builder(this).setTitle("Log").setView(ScrollView(this).apply { addView(tv) })
            .setPositiveButton("Copy") { _, _ -> copy(Job.logText()) }
            .setNegativeButton("Close", null).show()
    }

    private fun about() = io.execute {
        val doc = try { Py.module(this); Py.doctor } catch (e: Exception) { e.toString() }
        ui.post {
            AlertDialog.Builder(this).setTitle("ClipCutter ${packageManager.getPackageInfo(packageName, 0).versionName}")
                .setMessage("Everything runs on this phone: download, moment finding, editing.\n" +
                    "Only clip videos you have the rights to.\n\n$doc")
                .setPositiveButton("OK", null).show()
        }
    }

    private fun aiDialog() = io.execute {
        val m = Py.module(this)
        val services = JSONObject(m.callAttr("ai_services").toString())
        val status = JSONObject(m.callAttr("ai_status").toString())
        val keys = services.keys().asSequence().toList()
        ui.post {
            val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 16, 48, 0) }
            val note = TextView(this).apply {
                text = if (status.has("service")) "Using ${status.optString("service")} (${status.optString("model")})."
                       else "Optional. Without a key, hooks and titles come from built-in templates. " +
                            "A free key (NVIDIA, Groq, OpenRouter or Gemini) writes better ones."
                setTextColor(getColor(R.color.muted))
            }
            val spin = Spinner(this).apply {
                adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item,
                    keys.map { services.getString(it) })
                setSelection(keys.indexOf(status.optString("service")).coerceAtLeast(0))
            }
            val key = EditText(this).apply { hint = "Paste API key (empty = remove)"; isSingleLine = true }
            box.addView(note); box.addView(spin); box.addView(key)
            AlertDialog.Builder(this).setTitle("AI key").setView(box)
                .setPositiveButton("Save") { _, _ ->
                    val svc = keys[spin.selectedItemPosition]
                    val k = key.text.toString()
                    io.execute {
                        val r = JSONObject(m.callAttr("save_ai", svc, k).toString())
                        ui.post { toast(if (!r.optBoolean("ok")) r.optString("error") else if (k.isBlank()) "Key removed" else "Saved: ${r.optString("model")}") }
                    }
                }
                .setNegativeButton("Cancel", null).show()
        }
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_LONG).show()

    companion object { private const val PICK = 7 }
}
