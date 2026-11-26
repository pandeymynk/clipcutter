# ClipCutter for Android (offline APK)

The Android app is the same ClipCutter pipeline running on the phone itself: no server, no API key.
Paste a YouTube / Twitch / Kick link (or share it from the YouTube app, or pick a video from the phone).
The phone downloads the video, finds the best moments, and renders 9:16 clips with a hook, word-by-word
captions, a title, a caption and hashtags. An optional free AI key (same choices as the desktop app) writes better hooks.

Needs: an **arm64 phone on Android 10 or newer**, about 1 GB free storage (plus the video), and Wi-Fi for the download.

## Install

1. Download `ClipCutter-<version>-android-arm64.apk` from the GitHub release (or the "Android app" CI run's artifact).
2. Open it on the phone and allow "install unknown apps" for your browser/file manager when asked.
3. Xiaomi / POCO / Redmi: also turn off "MIUI optimization" prompts if the installer blocks it; Samsung: allow in Settings → Apps → Special access.

## Use

- Paste a link → choose how many clips → **Make clips**. You can lock the screen: the job runs in a
  foreground service with a progress notification and a wake lock.
- **Share** opens the Android share sheet (Instagram, YouTube, WhatsApp…). The post caption is copied to the
  clipboard first, because Instagram and TikTok ignore shared text: paste it in their caption box.
- **Save** copies the clip to `Movies/ClipCutter` (shows in the gallery). **Copy** copies title + caption.
- **Edit** opens the built-in editor (the desktop app has the same one): layout (auto, gameplay on top /
  person below, person on top, blurred, crop), a facecam box you drag and resize on a still of the video,
  captions on/off, language (Hinglish, as spoken in Hindi script, English via Whisper translate), style,
  position and size, caption words, hook text / hook replay / small title on/off, title and post caption.
  **Save & render** re-renders on the phone (about 25 s on the test emulator) and the preview shows the result.
- **Log** shows what the pipeline is doing; copy it when reporting a problem. **About** checks the built-in tools.

## How it works

| piece | Android choice | why |
|---|---|---|
| app shell | Kotlin, plain Android views, one screen + `ClipService` (foreground service) | small, no Compose/AppCompat |
| pipeline | **Chaquopy** (Python 3.13) running the shared `src/clipcutter` package unchanged | one codebase with the desktop app; a Kotlin rewrite would fork scoring/captions/hooks |
| Python deps | Chaquopy's Android wheels: numpy 1.26.2, Pillow 11.0, PyYAML, yt-dlp, yt-dlp-ejs, certifi | numpy 2.x / OpenCV have no Android 3.13 builds |
| ffmpeg / ffprobe | built by us: ffmpeg 8.1.3 + libx264, NDK r28 (`android/native/build.sh`) | ffmpeg-kit is retired; Media3 Transformer can't do the hook/blur/loudnorm/boom filter graph |
| YouTube JS challenge | **QuickJS-ng** `qjs` (built with the NDK), used by yt-dlp's EJS solver | deno/node have no Android builds |
| speech-to-text | **whisper.cpp** `whisper-cli`, model `ggml-base-q5_1` (60 MB, downloaded on first use) | only runs when the video has no captions |

Android 10+ only lets an app execute files from its native-library folder, so the four tools ship as
`lib/arm64-v8a/lib{ffmpeg,ffprobe,qjs,whisper}.so` (extracted at install: `useLegacyPackaging`).
`android_app.py` links them as `<files>/bin/ffmpeg` etc. and puts that on `PATH`, so the pipeline and
yt-dlp call them by name. Android-specific choices live in `system.py` (`IS_ANDROID`: fonts, x264 preset,
QuickJS runtime, whisper.cpp backend) and `analyze.py` (`_whisper_cpp`).

Self-repair: at start the app checks each tool and uses the first way that works: run it directly, run it
through Android's loader (`/system/bin/linker64`) for phones that block exec, or unpack a fresh copy from the
APK and run that through the loader. If Python can't look up a hostname, it asks Android's Java network stack.
The top of every job's Log says which way each tool runs. Before a download the app checks the internet and
explains how to unblock it (Xiaomi/POCO "Restrict data usage", Data Saver).

Files: app data in the app's private folder (`/data/data/app.clipcutter.android/files`: `output/`, `.work/`, `models/`).
Uninstalling the app deletes them; saved clips in `Movies/ClipCutter` stay.

## Build

```bash
# once: JDK 17, Android SDK + NDK 28.2, cmake, ninja, pkg-config, Python 3.13
export ANDROID_HOME=~/Library/Android/sdk ANDROID_NDK_HOME=$ANDROID_HOME/ndk/28.2.13676358
android/native/build.sh                  # ffmpeg+x264, qjs, whisper-cli, fonts (~10 min, cached after)
cd android && ./gradlew assembleDebug    # -> app/build/outputs/apk/debug/app-debug.apk
```

Chaquopy needs the same Python version on the build machine: set `CLIPCUTTER_BUILD_PYTHON=/path/to/python3.13`
if `python3.13` is not on `PATH` (e.g. `uv python find 3.13`). CI: `.github/workflows/android.yml` builds debug +
release APKs on every PR touching `android/`, and attaches the release APK to the draft release on a `v*` tag.
Release signing: add secrets `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`; without them
the release APK is signed with the debug key (fine for sideloading, not for the Play Store, and an APK signed
with a different key can't update it in place).

Test on an emulator or phone: `adb install -r app-debug.apk`, then
`adb shell am start -n app.clipcutter.android/.MainActivity --es autostart <url> --ei clips 1` starts a job,
and `adb logcat python.stdout:I '*:S'` shows the pipeline log.

## Tested (2026-11-25)

Android 11 arm64 emulator (Apple Silicon host, 4 cores, 4 GB RAM), Big Buck Bunny
(`https://www.youtube.com/watch?v=aqz-KE-bpKQ`, 10 min, 1080p60, no captions), fresh install, 2 clips:

| step | time |
|---|---|
| YouTube download (yt-dlp + QuickJS) | 90 s |
| loudness + scene cuts | 7 s |
| speech model download (60 MB) + whisper.cpp on 10 min | 70 s |
| render, per 19 s clip (1080x1920, x264 superfast) | 8 s |
| **total** | **184 s** |

Output: 1080x1920, 30 fps H.264 + AAC 48 kHz stereo, hook zoom + hook box, word-by-word captions, header,
blurred background, −16.6 LUFS. Share sheet and Save to gallery work.
The emulator runs on the Mac's fast cores: expect **2–4x slower** analysis/render on a mid-range phone
(e.g. Snapdragon 7xx/8xx from 2021) and more for a long video. Not yet tested on a real phone.

## Known limits

- **Emoji are left out** of hooks/captions on Android: Chaquopy's FreeType 2.9 can't draw colour-emoji fonts.
- **Hindi (Devanagari) captions** use the bundled Noto font, but Chaquopy's Pillow has no raqm/fribidi, so
  conjuncts and matras may not join correctly. Hinglish (Roman) captions, the default, are fine.
- **Facecam detection** uses Android's built-in face detector (no OpenCV for Android Python 3.13). It found the
  webcam in the GTA test stream; if it misses one, set the box by hand in the editor.
- **YouTube downloads break when YouTube changes**: the bundled yt-dlp is fixed at build time; update the app.
  "Confirm you're not a bot" errors depend on the network (mobile data vs Wi-Fi) and can't be fixed in the app.
- **Long videos** (> 2 h) are fetched audio-first and then per-clip sections, like the desktop app; that path,
  live mode, chat-replay download and campaign presets are untested on Android.
- **Picking a local video** copies it into the app first (ffmpeg needs a file path); not yet tested on a device.
- Renders use the CPU (no MediaCodec hardware encoder in our ffmpeg build). ffmpeg/x264 are built without SVE:
  some devices/emulators report SVE but trap it (SIGILL); NEON covers phones.
- arm64 only (no 32-bit or x86 phones). APK is ~60 MB (ffmpeg + ffprobe are 22 MB each).
