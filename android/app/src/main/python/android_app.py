"""Bridge between the Android app (Kotlin, via Chaquopy) and the shared clipcutter pipeline.

The Kotlin side calls setup() once, then run() from a foreground service thread. Everything
Android-specific in the pipeline itself lives in clipcutter/system.py (IS_ANDROID branches)."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

HOME: Path | None = None
TOOLS = {"ffmpeg": "libffmpeg.so", "ffprobe": "libffprobe.so", "qjs": "libqjs.so", "whisper-cli": "libwhisper.so"}


def setup(home: str, native_dir: str, resources: str) -> str:
    """home = app files dir, native_dir = nativeLibraryDir (where the arm64 tools are), resources = fonts etc."""
    global HOME
    HOME = Path(home)
    os.environ["CLIPCUTTER_HOME"] = home
    os.environ["CLIPCUTTER_NATIVE"] = native_dir
    os.environ["CLIPCUTTER_RESOURCES"] = resources
    # Name the tools the way the pipeline and yt-dlp call them ("ffmpeg", "ffprobe", "qjs").
    # nativeLibraryDir moves on every app update, so the links are refreshed each start.
    bin_dir = HOME / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, lib in TOOLS.items():
        link, target = bin_dir / name, Path(native_dir) / lib
        if link.is_symlink() or link.exists():
            if os.path.realpath(link) == str(target):
                continue
            link.unlink()
        if target.exists():
            link.symlink_to(target)
    os.environ["PATH"] = os.pathsep.join([str(bin_dir), os.environ.get("PATH", "/system/bin")])
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except ImportError:
        pass
    os.environ.setdefault("TMPDIR", str(HOME / "tmp"))
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    os.chdir(home)   # config.yaml / ai-settings.json live here, like the desktop app's data folder
    return doctor()


def doctor() -> str:
    """One line per tool, shown in the app's About box and the logs."""
    import subprocess
    lines = [f"python {sys.version.split()[0]} on {sys.platform}"]
    for name, args in (("ffmpeg", ["-version"]), ("ffprobe", ["-version"]), ("qjs", ["-h"]),
                       ("whisper-cli", ["-h"])):
        try:
            p = subprocess.run([name, *args], capture_output=True, text=True, timeout=20)
            out = (p.stdout or p.stderr).strip().splitlines()
            lines.append(f"{name}: {'ok' if out else 'no output'} {out[0][:60] if out else ''}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"{name}: MISSING ({e.__class__.__name__})")
    try:
        import yt_dlp.version
        lines.append(f"yt-dlp {yt_dlp.version.__version__}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"yt-dlp: MISSING ({e})")
    return "\n".join(lines)


def make_config(clips: int) -> dict:
    from clipcutter import config
    cfg = config.load()
    cfg["clips"] = int(clips)
    cfg["output_dir"] = str(HOME / "output")
    cfg["work_dir"] = str(HOME / ".work")
    try:
        import cv2  # noqa: F401  (no OpenCV build for Android yet: no facecam detection)
    except ImportError:
        if cfg["layout"] in ("auto", "split", "split_top") and not cfg.get("facecam"):
            cfg["layout"] = "blur"
    return cfg


def run(target: str, clips: int, listener) -> str:
    """Make clips. listener is a Kotlin object: progress(str, float), log(str), source(str), isCancelled()->bool.
    Returns JSON {out_dir, clips} or {error}."""
    from clipcutter import analyze, pipeline

    def log(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        try:
            listener.log(line)
        except Exception:
            pass

    pipeline.log = log
    pipeline.progress = lambda step, pct: listener.progress(step, float(pct))
    pipeline.on_source = lambda title: listener.source(title or "")
    pipeline.cancelled = lambda: bool(listener.isCancelled())
    analyze.on_model_progress = lambda text: listener.progress(text, -1.0)
    t0 = time.time()
    try:
        cfg = make_config(clips)
        out_dir, index = pipeline.run(target.strip(), cfg)
        log(f"total {time.time() - t0:.0f}s")
        return json.dumps({"out_dir": str(out_dir), "clips": index, "seconds": round(time.time() - t0)},
                          ensure_ascii=False)
    except pipeline.Cancelled:
        return json.dumps({"error": "Stopped."})
    except Exception as e:  # noqa: BLE001
        log(traceback.format_exc())
        return json.dumps({"error": friendly_error(e)})


def friendly_error(e: Exception) -> str:
    msg = str(e) or e.__class__.__name__
    low = msg.lower()
    if "sign in to confirm" in low or "not a bot" in low:
        return "YouTube asked to confirm you're not a bot. Try again later or on another network (Wi-Fi vs mobile data)."
    if "http error 403" in low:
        return "YouTube refused the download (HTTP 403). Update the app, or try again in a few minutes."
    if "unable to download" in low or "urlopen error" in low or "timed out" in low:
        return "Network problem while downloading. Check your connection and try again."
    if "no space left" in low:
        return "Your phone is out of storage. Free some space and try again."
    return msg[:300]


def list_clips() -> str:
    """All finished clips, newest first: [{dir, title, clips:[record + path]}]."""
    out = []
    root = HOME / "output"
    for idx in sorted(root.glob("*/index.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            recs = json.loads(idx.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in recs:
            r["path"] = str(idx.parent / r["file"])
        out.append({"dir": str(idx.parent), "title": (recs[0].get("source_title") if recs else idx.parent.name),
                    "clips": recs})
    return json.dumps(out, ensure_ascii=False)


def ai_status() -> str:
    from clipcutter import config
    ai = config.load_ai()
    return json.dumps({"service": ai.get("service"), "model": ai.get("api_model")} if ai.get("api_key") else {})


def ai_services() -> str:
    from clipcutter.writer import AI_SERVICES
    return json.dumps({k: v.get("name", k) for k, v in AI_SERVICES.items()})


def save_ai(service: str, key: str) -> str:
    """Optional free AI key (same box as the desktop app). Empty key removes it."""
    from clipcutter import config
    try:
        data = config.save_ai(service if key.strip() else None, key)
        return json.dumps({"ok": True, "model": data.get("api_model")})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(e)[:200]})
