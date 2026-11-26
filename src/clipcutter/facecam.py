"""Find the streamer's facecam overlay so the clip can use the split layout
(gameplay on top, facecam below) automatically."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from . import system


def _pngs(video: Path, start: float, end: float, n: int = 10, width: int = 960) -> list[bytes]:
    out = []
    for t in np.linspace(start, max(start + 0.5, end), n):
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", *system.hwaccel_args(), "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
             "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True,
        ).stdout
        if raw:
            out.append(raw)
    return out


def detect(video: Path, start: float, end: float) -> list[float] | None:
    """Facecam box [x, y, w, h] (fractions of the frame) from the video itself, or None."""
    backend = system.face_backend()
    if backend == "opencv":
        import cv2
        frames = [cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_GRAYSCALE) for b in _pngs(video, start, end)]
        return find([f for f in frames if f is not None])
    if backend == "android":   # no OpenCV on Android: the phone's own face detector
        pngs = _pngs(video, start, end, width=1280)
        faces, size = [], None
        for i, png in enumerate(pngs):
            W, H, boxes = _android_faces(png)
            size = size or (W, H)
            faces += [(i, *b) for b in boxes]
        found = _pick(faces, *size, len(pngs)) if size else None
        print(f"   facecam (phone detector): {len(faces)} faces in {len(pngs)} frames -> {found or 'none'}", flush=True)
        return found
    return None


def detect_files(paths: list[Path]) -> list[float] | None:
    """Same, from saved still frames (e.g. YouTube storyboard frames), upscaled so small faces are found."""
    import cv2

    frames = []
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            frames.append(cv2.resize(img, (img.shape[1] * 3, img.shape[0] * 3), interpolation=cv2.INTER_CUBIC))
    return find(frames, min_neighbors=4)


def find(frames: list, min_neighbors: int = 6) -> list[float] | None:
    """OpenCV: every face in every grayscale frame, then _pick() the facecam."""
    import cv2

    if not frames:
        return None
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    H, W = frames[0].shape[:2]
    faces = []
    for i, f in enumerate(frames):
        for x, y, w, h in cascade.detectMultiScale(f, scaleFactor=1.1, minNeighbors=min_neighbors,
                                                   minSize=(int(W * 0.03),) * 2):
            faces.append((i, x, y, w, h))
    return _pick(faces, W, H, len(frames))


def _android_faces(png: bytes) -> tuple[int, int, list[tuple[float, float, float, float]]]:
    """android.media.FaceDetector (built into every Android phone, offline) on one PNG frame."""
    from android.graphics import Bitmap, BitmapFactory, PointF
    from android.media import FaceDetector
    from java import jarray, jclass

    opts = BitmapFactory.Options()
    opts.inPreferredConfig = Bitmap.Config.RGB_565   # the detector only takes RGB_565
    bmp = BitmapFactory.decodeByteArray(png, 0, len(png), opts)
    W, H = bmp.getWidth() // 2 * 2, bmp.getHeight()
    if W != bmp.getWidth():
        bmp = Bitmap.createBitmap(bmp, 0, 0, W, H)
    faces = jarray(jclass("android.media.FaceDetector$Face"))(8)
    n = FaceDetector(W, H, 8).findFaces(bmp, faces)
    boxes = []
    for f in list(faces)[:n]:
        if f is None or f.confidence() < 0.3:
            continue
        mid, eyes = PointF(), f.eyesDistance()
        f.getMidPoint(mid)
        w, h = eyes * 2.2, eyes * 2.6           # roughly the face box OpenCV would give
        boxes.append((mid.x - w / 2, mid.y - h * 0.4, w, h))
    bmp.recycle()
    return W, H, boxes


def _pick(faces: list, W: int, H: int, n_frames: int) -> list[float] | None:
    """A facecam is a small face that stays in the same spot in most frames
    (a full-screen "just chatting" face is not a facecam). faces = [(frame, x, y, w, h)]."""
    # small faces only: bigger = a full-screen camera shot, not a webcam overlay
    faces_all = [(i, x + w / 2, y + h / 2, w, h) for i, x, y, w, h in faces if W * 0.03 <= w <= W * 0.14]
    # group faces by position: the facecam is the spot that has a face in the most frames
    clusters: list[list] = []
    for fc in faces_all:
        for c in clusters:
            cx0, cy0 = np.median([g[1] for g in c]), np.median([g[2] for g in c])
            if abs(fc[1] - cx0) < W * 0.06 and abs(fc[2] - cy0) < H * 0.09:
                c.append(fc)
                break
        else:
            clusters.append([fc])
    best = max(clusters, key=lambda c: len({g[0] for g in c}), default=None)
    if not best or len({g[0] for g in best}) < max(3, n_frames * 0.35):
        return None
    cx, cy, fw, fh = np.median(np.array([g[1:] for g in best]), axis=0)
    if abs(cx - W / 2) < W * 0.2 and abs(cy - H / 2) < H * 0.25:
        return None  # centered face = the video itself is a camera shot, not a webcam overlay
    # expand the face box to a webcam-shaped crop (~ 4:3), clamp to frame
    cw, ch = min(fw * 3.2, W * 0.5), min(fh * 2.6, H * 0.6)
    x0 = max(0.0, min(cx - cw / 2, W - cw))
    y0 = max(0.0, min(cy - ch / 2, H - ch))
    return [round(x0 / W, 4), round(y0 / H, 4), round(cw / W, 4), round(ch / H, 4)]
