#!/usr/bin/env bash
# Cross-compile the command-line tools the Python pipeline runs as subprocesses, for arm64 Android:
#   ffmpeg + ffprobe (with libx264), qjs (QuickJS-ng: yt-dlp's JavaScript runtime for YouTube),
#   whisper-cli (whisper.cpp: speech-to-text when a video has no captions).
# Output: android/app/src/main/jniLibs/arm64-v8a/lib{ffmpeg,ffprobe,qjs,whisper}.so
# (Android 10+ only lets apps exec files from the app's native-library folder, hence the lib*.so names.)
#
# Needs: ANDROID_NDK_HOME (NDK r27+), cmake, ninja, pkg-config, make, git.
set -euo pipefail

FFMPEG_TAG=${FFMPEG_TAG:-n8.1.3}
X264_REF=${X264_REF:-b35605ace3ddf7c1a5d67a2eb553f034aef41d55}   # x264 "stable" branch
QJS_TAG=${QJS_TAG:-v0.18.0}
WHISPER_TAG=${WHISPER_TAG:-v1.9.6}
API=${API:-29}            # Android 10
JOBS=${JOBS:-$(getconf _NPROCESSORS_ONLN)}

HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/.src
BUILD=$HERE/.build
PREFIX=$BUILD/prefix
OUT=$HERE/../app/src/main/jniLibs/arm64-v8a
mkdir -p "$SRC" "$BUILD" "$PREFIX" "$OUT"

NDK=${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-}}
[ -d "$NDK" ] || { echo "Set ANDROID_NDK_HOME to an Android NDK (r27+)"; exit 1; }
case "$(uname -s)" in
  Darwin) HOST_TAG=darwin-x86_64 ;;   # the mac NDK is universal but keeps this folder name
  *) HOST_TAG=linux-x86_64 ;;
esac
TC=$NDK/toolchains/llvm/prebuilt/$HOST_TAG
SYSROOT=$TC/sysroot
CC=$TC/bin/aarch64-linux-android$API-clang
CXX=$TC/bin/aarch64-linux-android$API-clang++
CMAKE_ANDROID=(-G Ninja -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake"
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-$API -DANDROID_STL=c++_static
  -DCMAKE_BUILD_TYPE=Release)

fetch() {   # fetch <name> <git url> <ref>
  local dir=$SRC/$1
  if [ ! -d "$dir/.git" ]; then
    git init -q "$dir"
    git -C "$dir" remote add origin "$2"
  fi
  if [ "$(git -C "$dir" rev-parse -q --verify HEAD 2>/dev/null)" != "$(git -C "$dir" rev-parse -q --verify "$3^{commit}" 2>/dev/null || echo none)" ]; then
    git -C "$dir" fetch -q --depth 1 origin "$3"
    git -C "$dir" checkout -q FETCH_HEAD
  fi
}

want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }

# ---------- x264 (static library) ----------
if want ffmpeg && [ ! -f "$PREFIX/lib/libx264.a.nosve" ]; then
  fetch x264 https://code.videolan.org/videolan/x264.git "$X264_REF"
  (cd "$SRC/x264" && make distclean >/dev/null 2>&1 || true
   CC=$CC ./configure --host=aarch64-linux-android --cross-prefix="$TC/bin/llvm-" --sysroot="$SYSROOT" \
     --prefix="$PREFIX" --enable-static --enable-pic --disable-cli --extra-cflags="-O3"
   # no SVE: some devices/emulators report it but trap the instructions (SIGILL); NEON is what phones use
   perl -pi -e 's/^#define HAVE_(SVE2?) 1/#define HAVE_$1 0/' config.h
   make -j"$JOBS" && make install && touch "$PREFIX/lib/libx264.a.nosve")
fi

# ---------- ffmpeg + ffprobe ----------
if want ffmpeg; then
  fetch ffmpeg https://git.ffmpeg.org/ffmpeg.git "$FFMPEG_TAG"
  (cd "$SRC/ffmpeg"
   PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig PKG_CONFIG_LIBDIR=$PREFIX/lib/pkgconfig ./configure \
     --prefix="$BUILD/ffmpeg" --target-os=android --arch=aarch64 --cpu=armv8-a --enable-cross-compile \
     --cc="$CC" --cxx="$CXX" --ar="$TC/bin/llvm-ar" --nm="$TC/bin/llvm-nm" --ranlib="$TC/bin/llvm-ranlib" \
     --strip="$TC/bin/llvm-strip" --sysroot="$SYSROOT" --pkg-config=pkg-config --pkg-config-flags=--static \
     --enable-pic --enable-gpl --enable-libx264 --enable-zlib --disable-autodetect \
     --enable-static --disable-shared --disable-doc --disable-ffplay --disable-debug --disable-devices --enable-indev=lavfi \
     --disable-sve --disable-sve2 --disable-sme --disable-sme2 \
     --disable-encoders --enable-encoder=libx264,aac,png,mjpeg,pcm_s16le,pcm_f32le,flac,libx264rgb,rawvideo,wrapped_avframe \
     --extra-cflags="-I$PREFIX/include -O3" --extra-ldflags="-L$PREFIX/lib"
   make -j"$JOBS" && make install)
  "$TC/bin/llvm-strip" -o "$OUT/libffmpeg.so" "$BUILD/ffmpeg/bin/ffmpeg"
  "$TC/bin/llvm-strip" -o "$OUT/libffprobe.so" "$BUILD/ffmpeg/bin/ffprobe"
fi

# ---------- QuickJS-ng (qjs) ----------
if want qjs; then
  fetch quickjs "https://github.com/quickjs-ng/quickjs.git" "$QJS_TAG"
  cmake -S "$SRC/quickjs" -B "$BUILD/quickjs" "${CMAKE_ANDROID[@]}" -DBUILD_SHARED_LIBS=OFF
  cmake --build "$BUILD/quickjs" --target qjs -j"$JOBS"
  "$TC/bin/llvm-strip" -o "$OUT/libqjs.so" "$BUILD/quickjs/qjs"
fi

# ---------- whisper.cpp (whisper-cli) ----------
if want whisper; then
  fetch whisper "https://github.com/ggml-org/whisper.cpp.git" "$WHISPER_TAG"
  cmake -S "$SRC/whisper" -B "$BUILD/whisper" "${CMAKE_ANDROID[@]}" -DBUILD_SHARED_LIBS=OFF \
    -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF -DWHISPER_SDL2=OFF -DWHISPER_CURL=OFF \
    -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF
  cmake --build "$BUILD/whisper" --target whisper-cli -j"$JOBS"
  "$TC/bin/llvm-strip" -o "$OUT/libwhisper.so" "$BUILD/whisper/bin/whisper-cli"
fi

# ---------- fonts (same Noto fonts as the desktop app; OFL) ----------
if want fonts; then
  FONTS=$HERE/../app/src/main/assets/fonts
  mkdir -p "$FONTS"
  NOTO=https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io/fonts
  for f in NotoSans/hinted/ttf/NotoSans-Black.ttf NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Bold.ttf; do
    [ -s "$FONTS/$(basename "$f")" ] || curl -fsSL -o "$FONTS/$(basename "$f")" "$NOTO/$f"
  done
  [ -s "$FONTS/OFL.txt" ] || curl -fsSL -o "$FONTS/OFL.txt" https://raw.githubusercontent.com/notofonts/devanagari/main/OFL.txt
fi

ls -l "$OUT"
