package app.clipcutter.android

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.max
import kotlin.math.min

/**
 * A still of the source video with the facecam box on it. Drag inside the box to move it,
 * drag the yellow corner to resize. [cam] is [x, y, w, h] as fractions of the frame, or null (= auto).
 */
class CamPickerView(ctx: Context, attrs: AttributeSet? = null) : View(ctx, attrs) {
    var bitmap: Bitmap? = null
        set(v) { field = v; requestLayout(); invalidate() }
    var cam: DoubleArray? = null
        set(v) { field = v; invalidate() }
    var onChange: (() -> Unit)? = null

    private val dim = Paint().apply { color = Color.argb(115, 0, 0, 0) }
    private val line = Paint().apply { color = Color.parseColor("#FFE600"); style = Paint.Style.STROKE; strokeWidth = 5f }
    private val knob = Paint().apply { color = Color.parseColor("#FFE600") }
    private val text = Paint().apply { color = Color.LTGRAY; textSize = 34f; textAlign = Paint.Align.CENTER; isAntiAlias = true }
    private var mode = 0          // 0 none, 1 move, 2 resize
    private var downX = 0f
    private var downY = 0f
    private var start = DoubleArray(4)

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        val b = bitmap
        val h = if (b != null && b.width > 0) w * b.height / b.width else w * 9 / 16
        setMeasuredDimension(w, h)
    }

    override fun onDraw(c: Canvas) {
        c.drawColor(Color.BLACK)
        bitmap?.let { c.drawBitmap(it, null, RectF(0f, 0f, width.toFloat(), height.toFloat()), null) }
        val r = box()
        if (r == null) {
            c.drawText("Auto: the app finds the facecam", width / 2f, height / 2f, text)
            return
        }
        c.drawRect(0f, 0f, width.toFloat(), r.top, dim)
        c.drawRect(0f, r.bottom, width.toFloat(), height.toFloat(), dim)
        c.drawRect(0f, r.top, r.left, r.bottom, dim)
        c.drawRect(r.right, r.top, width.toFloat(), r.bottom, dim)
        c.drawRect(r, line)
        c.drawCircle(r.right, r.bottom, 18f, knob)
    }

    private fun box(): RectF? = cam?.let {
        RectF((it[0] * width).toFloat(), (it[1] * height).toFloat(),
            ((it[0] + it[2]) * width).toFloat(), ((it[1] + it[3]) * height).toFloat())
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        val r = box() ?: return false
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                mode = when {
                    kotlin.math.hypot(e.x - r.right, e.y - r.bottom) < 60 -> 2
                    r.contains(e.x, e.y) -> 1
                    else -> 0
                }
                if (mode == 0) return false
                downX = e.x; downY = e.y; start = cam!!.copyOf()
                parent.requestDisallowInterceptTouchEvent(true)   // don't scroll the page while dragging
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                val dx = (e.x - downX) / width.toDouble()
                val dy = (e.y - downY) / height.toDouble()
                val (x, y, w, h) = start.toList()
                cam = if (mode == 1) doubleArrayOf(clamp(x + dx, 0.0, 1 - w), clamp(y + dy, 0.0, 1 - h), w, h)
                      else doubleArrayOf(x, y, clamp(w + dx, 0.05, 1 - x), clamp(h + dy, 0.05, 1 - y))
                onChange?.invoke()
                return true
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> { mode = 0; return true }
        }
        return super.onTouchEvent(e)
    }

    private fun clamp(v: Double, a: Double, b: Double) = max(a, min(b, v))
}
