package app.clipcutter.android

import android.app.Activity
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import android.widget.VideoView
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors

/** Built-in clip editor: layout + facecam box, captions (on/off, language, style, position, size, words),
 *  hook text/replay/header, title and post caption. Saving re-renders the clip on the phone. */
class EditorActivity : Activity() {
    private val ui = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private lateinit var path: String
    private var state = JSONObject()
    private var wordsEdited = false
    private var busy = false

    private val layouts = listOf("auto" to "Auto (find the facecam)", "split" to "Gameplay on top, person below",
        "split_top" to "Person on top, gameplay below", "blur" to "Full video, blurred background", "crop" to "Crop to fill")
    private val langs = listOf("hinglish" to "Hinglish", "original" to "As spoken (हिंदी)", "english" to "English")
    private val styles = listOf("genz" to "Gen Z", "hype" to "Hype", "clean" to "Clean")
    private val positions = listOf("low" to "Low", "middle" to "Middle", "high" to "High")
    private val sizes = listOf("small" to "Small", "normal" to "Normal", "big" to "Big")

    private lateinit var video: VideoView
    private lateinit var status: TextView
    private lateinit var cam: CamPickerView
    private val sp = HashMap<String, Pair<Spinner, List<Pair<String, String>>>>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_editor)
        path = intent.getStringExtra("path") ?: return finish()
        video = findViewById(R.id.edVideo)
        status = findViewById(R.id.edStatus)
        cam = findViewById(R.id.edCam)
        video.setOnClickListener { if (video.isPlaying) video.pause() else video.start() }   // tap = pause / play
        spinner("layout", R.id.edLayout, layouts)
        spinner("lang", R.id.edLang, langs)
        spinner("style", R.id.edStyle, styles)
        spinner("position", R.id.edPos, positions)
        spinner("size", R.id.edSize, sizes)
        sp["layout"]!!.first.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) = camSection()
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        cam.onChange = { if (value("layout") !in listOf("split", "split_top")) select("layout", "split") }
        findViewById<Button>(R.id.edAuto).setOnClickListener { cam.cam = null; select("layout", "auto") }
        mapOf(R.id.edTL to "top-left", R.id.edTR to "top-right", R.id.edBL to "bottom-left", R.id.edBR to "bottom-right")
            .forEach { (id, key) ->
                findViewById<Button>(id).setOnClickListener {
                    val p = state.optJSONObject("presets")?.optJSONArray(key) ?: return@setOnClickListener
                    cam.cam = DoubleArray(4) { p.getDouble(it) }
                    if (value("layout") !in listOf("split", "split_top")) select("layout", "split")
                }
            }
        findViewById<EditText>(R.id.edWords).addTextChangedListener(object : android.text.TextWatcher {
            override fun afterTextChanged(s: android.text.Editable?) { wordsEdited = true }
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
        })
        findViewById<Button>(R.id.edClose).setOnClickListener { finish() }
        findViewById<Button>(R.id.edSave).setOnClickListener { save() }
        load(loadFrame = true)
    }

    private fun spinner(key: String, id: Int, items: List<Pair<String, String>>) {
        val s = findViewById<Spinner>(id)
        s.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, items.map { it.second })
        sp[key] = s to items
    }

    private fun value(key: String): String = sp[key]!!.let { (s, items) -> items[s.selectedItemPosition].first }
    private fun select(key: String, v: String) = sp[key]!!.let { (s, items) ->
        s.setSelection(items.indexOfFirst { it.first == v }.coerceAtLeast(0)); camSection()
    }

    private fun camSection() {
        findViewById<View>(R.id.edCamSec).visibility =
            if (value("layout") in listOf("auto", "split", "split_top")) View.VISIBLE else View.GONE
    }

    private fun load(loadFrame: Boolean) = io.execute {
        val m = Py.module(this)
        val st = JSONObject(m.callAttr("editor_state", path).toString())
        val frame = if (loadFrame) m.callAttr("clip_frame", path).toString() else ""
        val bmp = if (frame.isNotEmpty()) BitmapFactory.decodeFile(frame) else null
        ui.post {
            state = st
            val o = st.getJSONObject("options")
            listOf("layout", "lang", "style", "position", "size").forEach { select(it, o.optString(it)) }
            findViewById<CheckBox>(R.id.edCapsOn).isChecked = o.optBoolean("captions", true)
            findViewById<CheckBox>(R.id.edHookText).isChecked = o.optBoolean("hook_text", true)
            findViewById<CheckBox>(R.id.edReplay).isChecked = o.optBoolean("hook_replay", true)
            findViewById<CheckBox>(R.id.edHeader).isChecked = o.optBoolean("header", true)
            findViewById<EditText>(R.id.edWords).setText(st.optString("captions"))
            findViewById<EditText>(R.id.edHook).setText(st.optString("hook"))
            findViewById<EditText>(R.id.edTitle).setText(st.optString("title"))
            findViewById<EditText>(R.id.edCaption).setText(st.optString("post_caption"))
            wordsEdited = false
            cam.cam = o.optJSONArray("facecam")?.let { a -> DoubleArray(4) { a.getDouble(it) } }
            if (bmp != null) cam.bitmap = bmp
            if (!st.optBoolean("has_video")) status.text = "The downloaded video is gone: only title and caption can be changed."
            playPreview()
        }
    }

    private fun playPreview() {
        video.setVideoURI(Uri.fromFile(File(path)))   // same app's private file: no FileProvider needed
        video.setOnPreparedListener { it.isLooping = true; video.start() }
    }

    private fun save() {
        if (busy) return
        if (Job.running) { status.text = "Wait for the current clipping job to finish."; return }
        val opts = JSONObject()
        listOf("layout", "lang", "style", "position", "size").forEach { opts.put(it, value(it)) }
        opts.put("captions", findViewById<CheckBox>(R.id.edCapsOn).isChecked)
        opts.put("hook_text", findViewById<CheckBox>(R.id.edHookText).isChecked)
        opts.put("hook_replay", findViewById<CheckBox>(R.id.edReplay).isChecked)
        opts.put("header", findViewById<CheckBox>(R.id.edHeader).isChecked)
        opts.put("facecam", cam.cam?.let { c -> JSONArray().apply { c.forEach { put(Math.round(it * 10000) / 10000.0) } } } ?: JSONObject.NULL)
        val words = if (wordsEdited) findViewById<EditText>(R.id.edWords).text.toString() else null
        val title = findViewById<EditText>(R.id.edTitle).text.toString()
        val caption = findViewById<EditText>(R.id.edCaption).text.toString()
        val hook = findViewById<EditText>(R.id.edHook).text.toString()
        busy = true
        val btn = findViewById<Button>(R.id.edSave)
        btn.isEnabled = false; btn.text = "Rendering…"
        status.text = if (value("lang") == "english") "Rendering… English captions take longer the first time." else "Rendering…"
        video.stopPlayback()
        io.execute {
            val r = try {
                JSONObject(Py.module(this).callAttr("edit_clip", path, title, caption, hook, words, opts.toString()).toString())
            } catch (e: Exception) { JSONObject().put("ok", false).put("error", e.message) }
            ui.post {
                busy = false
                btn.isEnabled = true; btn.text = "Save & render"
                status.text = if (r.optBoolean("ok")) "Saved ✓ The preview shows the new clip." else r.optString("error")
                setResult(RESULT_OK)
                load(loadFrame = false)
            }
        }
    }

    override fun onDestroy() {
        video.stopPlayback()
        super.onDestroy()
    }
}
