package app.clipcutter.android

/** State of the one clipping job, shared by the service (writer) and the screen (reader). */
object Job {
    @Volatile var running = false
    @Volatile var status = ""
    @Volatile var pct = 0.0
    @Volatile var title = ""
    @Volatile var target = ""
    @Volatile var startedAt = 0L
    @Volatile var finishedAt = 0L
    @Volatile var cancel = false
    @Volatile var error: String? = null
    @Volatile var resultSeconds = 0L
    /** Bumped every time a job ends, so the screen knows to reload the clip list. */
    @Volatile var generation = 0

    private val lines = ArrayDeque<String>()

    fun log(line: String) = synchronized(lines) {
        lines.addLast(line)
        while (lines.size > 400) lines.removeFirst()
    }

    fun logText(): String = synchronized(lines) { lines.joinToString("\n") }

    fun reset(target: String) {
        this.target = target
        running = true; cancel = false; error = null
        status = "Starting…"; pct = 0.0; title = ""
        startedAt = System.currentTimeMillis(); finishedAt = 0L
        synchronized(lines) { lines.clear() }
    }
}

/** Called from Python (Chaquopy) while the pipeline runs. */
class Listener(private val onChange: () -> Unit) {
    fun progress(step: String, pct: Double) {
        Job.status = step
        if (pct >= 0) Job.pct = pct
        onChange()
    }

    fun log(line: String) = Job.log(line)

    fun source(title: String) {
        Job.title = title
        onChange()
    }

    fun isCancelled(): Boolean = Job.cancel
}
