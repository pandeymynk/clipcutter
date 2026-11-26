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


LINKER = "/system/bin/linker64"
PROBE = {"ffmpeg": ["-version"], "ffprobe": ["-version"], "qjs": ["-e", "0"], "whisper-cli": ["-h"]}
RUN: dict[str, list[str]] = {}      # tool name -> command prefix that works on this phone
TOOL_NOTES: dict[str, str] = {}     # tool name -> how it runs / why it doesn't (shown in About and the Log)


def setup(home: str, native_dir: str, resources: str, apk: str = "") -> str:
    """home = app files dir, native_dir = nativeLibraryDir (where the arm64 tools are), resources = fonts etc.,
    apk = the installed APK (the tools are unpacked from it if a phone didn't install them properly)."""
    global HOME
    HOME = Path(home)
    dbg = HOME / "debug.env"   # testing only (adb run-as): e.g. CLIPCUTTER_FORCE_UNPACK=1
    if dbg.exists():
        for line in dbg.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
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
        link.symlink_to(target)   # even if missing: yt-dlp finds tools by name on PATH; the launcher fixes the rest
    os.environ["PATH"] = os.pathsep.join([str(bin_dir), os.environ.get("PATH", "/system/bin")])
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except ImportError:
        pass
    os.environ.setdefault("TMPDIR", str(HOME / "tmp"))
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    os.chdir(home)   # config.yaml / ai-settings.json live here, like the desktop app's data folder
    for name, lib in TOOLS.items():
        _resolve(name, Path(native_dir) / lib, apk)
    _patch_subprocess()
    _patch_dns()
    return doctor()


def _works(cmd: list[str]) -> tuple[bool, str]:
    """Can this command start at all? (A non-zero exit is fine; exec errors and crashes are not.)"""
    import subprocess
    try:
        p = _orig_run(cmd, capture_output=True, timeout=60)
    except OSError as e:
        return False, f"{e.__class__.__name__} [Errno {e.errno}] {e.strerror}"
    except subprocess.TimeoutExpired:
        return False, "timed out"
    if p.returncode < 0 or p.returncode in (126, 127):
        return False, f"exit {p.returncode} {p.stderr[-120:]!r}"
    return True, ""


def _resolve(name: str, lib: Path, apk: str) -> None:
    """Find a way to run a bundled tool on this phone:
    1) run it from the app's native-library folder (normal),
    2) run it through Android's loader (/system/bin/linker64), for phones that block exec there,
    3) unpack a fresh copy from the APK and run that through the loader (tool missing or damaged)."""
    tries: list[tuple[str, list[str]]] = []
    if os.environ.get("CLIPCUTTER_FORCE_UNPACK"):
        lib = Path("/nonexistent") / lib.name
    if lib.exists() and not os.environ.get("CLIPCUTTER_FORCE_LINKER"):
        tries.append(("direct", [str(lib)]))
    if lib.exists() and os.path.exists(LINKER):
        tries.append(("loader", [LINKER, str(lib)]))
    errors = []
    for mode, cmd in tries:
        ok, err = _works(cmd + PROBE[name])
        if ok:
            RUN[name], TOOL_NOTES[name] = cmd, mode
            return
        errors.append(f"{mode}: {err}")
    copy = _unpack(lib.name, apk, errors)
    if copy and os.path.exists(LINKER):
        ok, err = _works([LINKER, str(copy)] + PROBE[name])
        if ok:
            RUN[name], TOOL_NOTES[name] = [LINKER, str(copy)], "unpacked from APK"
            return
        errors.append(f"unpacked: {err}")
    TOOL_NOTES[name] = "NOT WORKING (" + "; ".join(errors or ["file missing"]) + ")"


def _unpack(lib_name: str, apk: str, errors: list) -> Path | None:
    import zipfile
    dest = HOME / "tools" / lib_name
    try:
        with zipfile.ZipFile(apk) as z:
            info = z.getinfo(f"lib/arm64-v8a/{lib_name}")
            if not (dest.exists() and dest.stat().st_size == info.file_size):
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(f"{dest}.part", "wb") as out:
                    while chunk := src.read(1 << 20):
                        out.write(chunk)
                os.replace(f"{dest}.part", dest)
        dest.chmod(0o700)
        return dest
    except Exception as e:  # noqa: BLE001
        errors.append(f"unpack: {e}")
        return None


import subprocess as _sp  # noqa: E402
_orig_run = _sp.run
_orig_popen_init = _sp.Popen.__init__


def _patch_subprocess() -> None:
    """Every call of a bundled tool by name or path (pipeline, yt-dlp) goes through the way found above."""
    if getattr(_sp.Popen.__init__, "_cc", False):
        return

    def init(self, args, *a, **k):
        if isinstance(args, (list, tuple)) and args:
            name = os.path.basename(str(args[0]))
            if name in RUN:
                args = [*RUN[name], *args[1:]]
        _orig_popen_init(self, args, *a, **k)
    init._cc = True
    _sp.Popen.__init__ = init


def _patch_dns() -> None:
    """If Python's name lookup fails ([Errno 7]/[Errno 8]) ask Android's Java network stack instead."""
    import socket
    orig = socket.getaddrinfo
    if getattr(orig, "_cc", False):
        return

    def gai(host, port, family=0, type=0, proto=0, flags=0):
        try:
            if os.environ.get("CLIPCUTTER_FORCE_JAVA_DNS") and host and not host[0].isdigit():
                raise socket.gaierror(8, "forced for testing")
            return orig(host, port, family, type, proto, flags)
        except socket.gaierror:
            if not host or isinstance(host, bytes):
                raise
            try:
                from java.net import InetAddress
                ips = [a.getHostAddress() for a in InetAddress.getAllByName(host)]
            except Exception:  # noqa: BLE001
                raise socket.gaierror(8, f"can't find {host}: no internet for ClipCutter?") from None
            num = port if isinstance(port, int) else (int(port) if str(port or "0").isdigit()
                                                      else socket.getservbyname(str(port)))
            out = []
            for ip in ips:
                fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
                if family not in (0, socket.AF_UNSPEC, fam):
                    continue
                addr = (ip.split("%")[0], num, 0, 0) if fam == socket.AF_INET6 else (ip, num)
                for st in ([type] if type else [socket.SOCK_STREAM]):
                    out.append((fam, st, proto or 6, "", addr))
            if not out:
                raise
            return out
    gai._cc = True
    socket.getaddrinfo = gai


def doctor() -> str:
    """One line per tool, shown in the app's About box and at the top of every job's Log."""
    import platform
    lines = [f"python {sys.version.split()[0]} on {sys.platform} {platform.machine()}"]
    for name in TOOLS:
        lines.append(f"{name}: {TOOL_NOTES.get(name, 'not checked')}")
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
    for line in doctor().splitlines():
        log(line)
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
    if "errno 7" in low or "errno 8" in low and ("host" in low or "name" in low or "address" in low):
        return ("No internet for ClipCutter. Check Wi-Fi, and on Xiaomi/POCO: Settings → Apps → Manage apps → "
                "ClipCutter → Restrict data usage → tick Wi-Fi and Mobile data.")
    if "exec format" in low or "errno 8" in low or "permission denied" in low and "lib" in low:
        return "A built-in tool couldn't start on this phone. Tap Log → Copy and send it to the developer."
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


def edit_clip(path: str, title, post_caption, hook, captions) -> str:
    """Edit box: title/post caption are saved; a new hook or new caption words re-render the clip.
    Arguments left as None (null from Kotlin) are not changed."""
    from clipcutter import pipeline
    try:
        p = Path(path)
        rec = pipeline.edit_clip(p.parent, p.name, make_config(1), title=title, post_caption=post_caption,
                                 hook=hook, captions=captions)
        return json.dumps({"ok": True, "hook": rec.get("hook")}, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        print(traceback.format_exc(), flush=True)
        return json.dumps({"ok": False, "error": friendly_error(e)}, ensure_ascii=False)
