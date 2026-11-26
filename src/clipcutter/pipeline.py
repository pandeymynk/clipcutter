"""Stream in -> ready-to-post clips out."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from . import analyze, ingest, render, score, writer


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def on_source(title: str) -> None:
    """Overridden by the web app to show the video's title on the loader."""


class Cancelled(Exception):
    pass


def cancelled() -> bool:
    """Overridden by the web app's Stop button."""
    return False


def _check() -> None:
    if cancelled():
        raise Cancelled("stopped by user")


def progress(step: str, pct: float) -> None:
    """Overridden by the web app to drive the loader. pct is 0-100 for the whole job."""


# share of the progress bar each phase gets
DL, ANALYZE, TRANSCRIBE, RENDER = (0, 30), (30, 34), (34, 62), (62, 100)
FULL_TRANSCRIPT_MAX = 90 * 60   # up to 90 min: transcribe everything once (like Opus Clip); longer: only candidates
CHUNK = 300                     # transcribe in 5-minute chunks so the loader can show progress


def _span(phase: tuple[int, int], frac: float) -> float:
    return phase[0] + (phase[1] - phase[0]) * max(0.0, min(1.0, frac))


def _transcribe_cached(pcm, a: float, b: float, cfg: dict, work: Path) -> list[dict]:
    cache = work / "transcripts" / f"{int(a)}_{int(b)}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    words = analyze.transcribe_window(pcm, a, b, cfg["whisper_model"], cfg["language"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(words))
    return words


def _full_transcript(pcm, T: int, cfg: dict, work: Path) -> list[dict]:
    cache = work / "transcript.json"
    if cache.exists():
        return json.loads(cache.read_text())
    words: list[dict] = []
    n = max(1, -(-T // CHUNK))
    for i in range(n):
        _check()
        a, b = i * CHUNK, min(T, (i + 1) * CHUNK)
        progress(f"Listening to the whole video… {a // 60}–{b // 60} of {T // 60} min",
                 _span(TRANSCRIBE, i / n))
        words += analyze.transcribe_window(pcm, a, b, cfg["whisper_model"], cfg["language"])
    cache.write_text(json.dumps(words, ensure_ascii=False))
    return words


def run(target: str, cfg: dict, chat: str | None = None, out_sub: str = "") -> tuple[Path, list[dict]]:
    t_start = time.time()
    work_root = Path(cfg["work_dir"])
    log(f"ingest: {target}")
    progress("Getting video info…", 1)
    ingest.on_download = lambda f: progress(f"Downloading video… {int(f * 100)}%", _span(DL, f))
    src = ingest.fetch(target, work_root, chat)
    on_source(src.title)
    work = work_root / src.id
    work.mkdir(parents=True, exist_ok=True)
    out_dir = Path(cfg["output_dir"]) / out_sub / src.id if out_sub else Path(cfg["output_dir"]) / src.id
    out_dir.mkdir(parents=True, exist_ok=True)

    info = analyze.probe(src.audio)
    T = int(info["duration"])
    kind = f"video {info['width']}x{info['height']}" if src.video else "long stream: audio only, video parts fetched per clip"
    log(f"{src.title[:60]!r}: {kind}, {T // 3600}h{T % 3600 // 60:02d}m, chat: {src.chat.name if src.chat else 'none'}")

    log("analyze: loudness, scene cuts, chat")
    progress("Finding the best moments (audio, chat, action)…", _span(ANALYZE, 0.1))
    pcm = analyze.load_audio(src.audio, work)
    db = analyze.loudness(pcm, T)
    cuts = analyze.scene_cuts(src.video, T, work) if src.video else None
    chat_rate, chat_samples = analyze.chat_activity(src.chat, T, cfg["chat_delay"])

    full = T <= FULL_TRANSCRIPT_MAX
    all_words = None
    if src.subs:
        progress("Reading the video's captions…", _span(TRANSCRIBE, 0.5))
        all_words = ingest.caption_words(src.subs)
        full = True
        log(f"transcript: {len(all_words)} words from platform captions ({src.subs.name}), no speech-to-text needed")
    elif full:
        log("transcribe: whole video (no captions available)")
        all_words = _full_transcript(pcm, T, cfg, work)
    progress("Picking the best moments…", _span(TRANSCRIBE, 1.0))

    w = cfg["weights"]
    signals = {
        "audio": score.audio_signal(db),
        "visual": score.visual_signal(cuts) if cuts is not None else None,
        "chat": score.chat_signal(chat_rate) if chat_rate is not None else None,
        "speech": score.speech_signal(all_words, T) if all_words else None,
    }
    base = score.combine(signals, w)
    if cfg.get("window"):   # e.g. skip the "just chatting" start of a stream
        lo, hi = cfg["window"]
        lo = int(lo or 0); hi = int(hi) if hi else len(base)
        base[:lo] = 0
        base[hi:] = 0
        log(f"window: only moments between {lo // 60}m and {hi // 60}m")
    n = cfg["clips"]
    cands = score.candidates(base, max(6, n * 3), gap=int(cfg["max_len"] * 0.6))
    log(f"score: {len(cands)} candidate moments")

    for i, m in enumerate(cands, 1):
        a = max(0.0, m.peak - cfg["max_len"] - 5)
        b = min(info["duration"], m.peak + 20)
        if full:
            words = [x for x in all_words if a <= x["s"] <= b]
        else:
            progress(f"Listening to moment {i} of {len(cands)}…", _span(TRANSCRIBE, (i - 1) / len(cands)))
            words = _transcribe_cached(pcm, a, b, cfg, work)
        score.shape(m, words, cfg["min_len"], cfg["max_len"], info["duration"])
        m.speech = score.speech_hype(m)
        m.score = round((1 - w["speech"]) * m.base + w["speech"] * m.speech, 4)
        for k, sig in signals.items():
            if sig is not None and sig[m.peak] > 0.5:
                m.reasons.append(k)
        if m.speech > 0.4 and "speech" not in m.reasons:
            m.reasons.append("speech")
        print(f"   {i:2d}. peak {m.peak // 60}:{m.peak % 60:02d}  score {m.score:.2f}  {'+'.join(m.reasons) or '-'}")

    chosen = score.pick(cands, n)
    log(f"making {len(chosen)} clips")
    index = []
    used_hooks: set[str] = set()
    for k, m in enumerate(chosen, 1):
        _check()
        base_f = (k - 1) / len(chosen)
        step_f = 1 / len(chosen)
        out = out_dir / f"clip_{k:02d}.mp4"
        rec_path = out_dir / f"clip_{k:02d}.json"
        if out.exists() and out.stat().st_size > 0 and rec_path.exists():   # resume: already made
            old = json.loads(rec_path.read_text())
            if abs(old.get("start", -1) - m.start) < 0.01 and abs(old.get("end", -1) - m.end) < 0.01:
                index.append(old)
                used_hooks.add(old.get("hook", "").lower())
                log(f"{out.name} already made, skipping")
                continue
        t_clip = time.time()
        progress(f"Clip {k} of {len(chosen)}: writing hook…", _span(RENDER, base_f))
        # hook = the loudest second right around the peak, replayed first
        lo, hi = max(int(m.start), m.peak - 3), min(int(m.end) - 1, m.peak + 3)
        peak = lo + int(np.argmax(db[lo:hi + 1])) if hi >= lo else m.peak
        hook_cfg = cfg["hook"]
        hook_start = max(m.start, peak - 1.0)
        hook_dur = min(hook_cfg["seconds"], m.end - hook_start) if hook_cfg["enabled"] else 0.0

        transcript = " ".join(x["w"] for x in m.words)
        chat_near = [msg for s in range(m.peak - 3, m.peak + 8) for msg in chat_samples.get(s, [])]
        meta = writer.write(transcript, chat_near, cfg, seed=m.peak, title=src.title, avoid=used_hooks)
        used_hooks.add(meta["hook"].lower())

        clip = {"start": m.start, "end": m.end, "peak": float(peak), "hook_start": hook_start,
                "hook_dur": hook_dur, "words": m.words, "hook": meta["hook"]}
        clip_work = work / f"clip_{k:02d}"
        log(f"render {out.name}: {m.start:.1f}-{m.end:.1f}s  hook: \"{meta['hook']}\"  ({meta['writer']})")
        if src.video:
            progress(f"Clip {k} of {len(chosen)}: editing (hook, captions, 9:16)…", _span(RENDER, base_f + step_f * 0.2))
            render.render(clip, info, src.video, cfg, out, clip_work)
            video_path, offset = src.video, 0.0
        else:
            a = max(0.0, min(m.start, hook_start) - 3)
            b = min(info["duration"], max(m.end, hook_start + hook_dur) + 3)
            progress(f"Clip {k} of {len(chosen)}: downloading video part…", _span(RENDER, base_f + step_f * 0.1))
            ingest.on_download = lambda f, k=k, b0=base_f, st=step_f: progress(
                f"Clip {k} of {len(chosen)}: downloading video part… {int(f * 100)}%",
                _span(RENDER, b0 + st * 0.5 * f))
            section = ingest.download_section(src.url, a, b, clip_work / "section.mp4")
            progress(f"Clip {k} of {len(chosen)}: editing (hook, captions, 9:16)…", _span(RENDER, base_f + step_f * 0.55))
            shifted = _shift(clip, a)
            render.render(shifted, analyze.probe(section), section, cfg, out, clip_work)
            clip["layout"] = shifted.get("layout")
            video_path, offset = section, a

        record = {
            "file": out.name, "source": src.url or str(src.video), "source_title": src.title,
            "creator": src.uploader,
            "start": m.start, "end": m.end, "peak": peak, "score": m.score,
            "virality": virality(m.score), "layout": clip.get("layout"),
            "signals": m.reasons, "transcript": transcript, **meta,
            "post_caption": f"{meta['description']} {' '.join(meta['hashtags'])}".strip(),
            # for edit_clip(): re-render with new hook/caption text without re-downloading
            "words": m.words, "video": str(video_path), "offset": offset,
        }
        if cfg.get("campaign"):   # the brief's exact caption text + hashtags
            from . import campaigns
            record["campaign"] = cfg["campaign"]
            record["post_caption"] = campaigns.post_caption(cfg["campaign"], writer.censor(meta["hook"]))
        rec_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        index.append(record)
        # update the list after EVERY clip so the dashboard shows clips as soon as they're ready
        (out_dir / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
        log(f"{out.name} ready in {time.time() - t_clip:.0f}s")

    (out_dir / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
    progress(f"Done: {len(index)} clips ready", 100)
    log(f"done in {time.time() - t_start:.0f}s -> {out_dir}")
    return out_dir, index


def virality(s: float) -> int:
    """0-99 score shown to the user (like Opus Clip's), from our 0-1 moment score."""
    return int(max(1, min(99, round(99 * max(0.0, s) ** 0.6))))


def rerender(out_dir: str, cfg: dict) -> None:
    """Re-edit finished clips from the cached video sections (no network): new layout/campaign/captions.
    Useful when the platform rate-limits (e.g. YouTube 'confirm you're not a bot')."""
    out = Path(out_dir)
    work = Path(cfg["work_dir"]) / out.name
    vid = out.name.split("_", 1)[1].lower()
    subs = sorted((f for f in (Path(cfg["work_dir"]) / "downloads").glob("*.json3") if vid in f.name.lower()),
                  key=lambda f: "-orig" not in f.name)
    words = ingest.caption_words(subs[0]) if subs else []
    for rec_path in sorted(out.glob("clip_*.json")):
        rec = json.loads(rec_path.read_text())
        section = work / rec_path.stem / "section.mp4"
        if not section.exists():
            log(f"{rec_path.stem}: no cached section, skipped")
            continue
        start, end, peak = rec["start"], rec["end"], rec["peak"]
        hook_start = max(start, peak - 1.0)
        hook_dur = min(cfg["hook"]["seconds"], end - hook_start) if cfg["hook"]["enabled"] else 0.0
        clip_words = [w for w in words if start <= w["s"] < end]
        if not clip_words:
            log(f"{rec_path.stem}: no caption words found, rendering without captions")
        clip = {"start": start, "end": end, "peak": peak, "hook_start": hook_start, "hook_dur": hook_dur,
                "words": clip_words, "hook": rec["hook"]}
        a = max(0.0, min(start, hook_start) - 3)
        shifted = _shift(clip, a)
        mp4 = out / f"{rec_path.stem}.mp4"
        render.render(shifted, analyze.probe(section), section, cfg, mp4, work / rec_path.stem)
        rec["layout"] = shifted.get("layout")
        if cfg.get("campaign"):
            from . import campaigns
            rec["campaign"] = cfg["campaign"]
            rec["post_caption"] = campaigns.post_caption(cfg["campaign"], writer.censor(rec["hook"]))
        rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        log(f"{mp4.name} re-rendered ({rec['layout']})")


def edit_clip(out_dir: str | Path, name: str, cfg: dict, title: str | None = None,
              post_caption: str | None = None, hook: str | None = None, captions: str | None = None) -> dict:
    """Edit a finished clip. Title/post caption are saved as text; a new hook or new on-video caption words
    re-render the clip from the downloaded video (word timings are kept, or spread over the clip if the
    number of words changed). Returns the updated record."""
    out = Path(out_dir)
    stem = Path(name).stem
    rec_path, mp4 = out / f"{stem}.json", out / f"{stem}.mp4"
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    if title is not None:
        rec["title"] = title.strip()
    if post_caption is not None:
        rec["post_caption"] = post_caption.strip()
    rerender = False
    if hook is not None and hook.strip() and hook.strip() != rec.get("hook"):
        rec["hook"] = hook.strip()
        rerender = True
    words = rec.get("words") or _spread(rec.get("transcript", "").split(), rec["start"], rec["end"])
    if captions is not None and captions.split() != [w["w"] for w in words]:
        words = _retime(words, captions.split(), rec["start"], rec["end"])
        rerender = True
    rec["words"], rec["transcript"] = words, " ".join(w["w"] for w in words)
    _save_record(out, rec_path, rec)   # text edits are kept even if the re-render below fails
    if not rerender:
        return rec
    video, offset = _clip_source(rec, out, stem, cfg)
    if not video:
        raise RuntimeError("The downloaded video for this clip is gone, so the hook/captions can't be re-rendered. "
                           "Title and post caption were saved.")
    if rec.get("campaign"):
        from . import campaigns
        cfg = json.loads(json.dumps(cfg))
        campaigns.apply(cfg, rec["campaign"])   # same CTA / logo / censoring as the first render
    cfg = {**cfg, "layout": rec.get("layout") or cfg["layout"]}
    start, end, peak = rec["start"], rec["end"], rec["peak"]
    hook_start = max(start, peak - 1.0)
    hook_dur = min(cfg["hook"]["seconds"], end - hook_start) if cfg["hook"]["enabled"] else 0.0
    clip = {"start": start, "end": end, "peak": peak, "hook_start": hook_start, "hook_dur": hook_dur,
            "words": words, "hook": rec["hook"]}
    if offset:
        clip = _shift(clip, offset)
    tmp = out / f"{stem}.edit.mp4"
    work = Path(cfg["work_dir"]) / out.name / f"{stem}_edit"
    render.render(clip, analyze.probe(video), video, cfg, tmp, work)
    tmp.replace(mp4)
    return rec


def _clip_source(rec: dict, out: Path, stem: str, cfg: dict) -> tuple[Path | None, float]:
    """The downloaded video a clip was cut from, and where it starts in the original (0 for full videos).
    Clips made before records stored "video" are matched to .work/downloads like rerender() does."""
    if rec.get("video") and Path(rec["video"]).is_file():
        return Path(rec["video"]), float(rec.get("offset") or 0.0)
    work = Path(cfg["work_dir"])
    for f in (work / "downloads").glob("*.video.*"):
        if f.suffix in ingest.MEDIA_EXT and ingest._slug(f.name.split(".video.")[0]).lower() == out.name:
            return f, 0.0
    section = work / out.name / stem / "section.mp4"
    if section.is_file():
        hook_start = max(rec["start"], rec["peak"] - 1.0)
        return section, max(0.0, min(rec["start"], hook_start) - 3)
    src = rec.get("source") or ""
    if src and not src.startswith("http") and Path(src).is_file():   # local file
        return Path(src), 0.0
    return None, 0.0


def _save_record(out: Path, rec_path: Path, rec: dict) -> None:
    rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    idx = out / "index.json"
    try:
        items = json.loads(idx.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    items = [rec if it.get("file") == rec["file"] else it for it in items]
    idx.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def _spread(tokens: list[str], a: float, b: float) -> list[dict]:
    """Give words without timings an even share of [a, b], longer words a bit more."""
    if not tokens:
        return []
    weights = [len(t) + 2 for t in tokens]
    total, t, words = sum(weights), a, []
    for tok, wt in zip(tokens, weights):
        d = (b - a) * wt / total
        words.append({"w": tok, "s": round(t, 2), "e": round(t + d, 2)})
        t += d
    return words


def _retime(old: list[dict], tokens: list[str], start: float, end: float) -> list[dict]:
    """New caption words: same count keeps each word's timing; otherwise spread over the old words' span."""
    if len(tokens) == len(old):
        return [{**w, "w": tok} for w, tok in zip(old, tokens)]
    a = old[0]["s"] if old else start
    b = old[-1]["e"] if old else end
    return _spread(tokens, a, b)


def _shift(clip: dict, offset: float) -> dict:
    """Move clip times from the full stream onto a downloaded section starting at `offset`."""
    c = dict(clip)
    for k in ("start", "end", "peak", "hook_start"):
        c[k] = clip[k] - offset
    c["words"] = [{**w, "s": w["s"] - offset, "e": w["e"] - offset} for w in clip["words"]]
    return c
