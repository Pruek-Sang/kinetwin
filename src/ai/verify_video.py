"""Full verification of a real hand video (Cipher's 3-layer eyes).

  1. NUMBERS  -> MediaPipe: how many frames detected a hand + Speed/Acc/Quality
  2. ANNOTATED -> draws the 21-landmark skeleton on every frame (YOU watch)
  3. VISION   -> moondream (Ollama) describes ~6 key frames in text (Cipher reads)

Nothing leaves the machine (local MediaPipe + local Ollama). Run:

    python src\\ai\\verify_video.py <video_path>
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import cv2  # noqa: E402

from ai.validate_video import validate  # noqa: E402

OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "moondream"
N_KEYFRAMES = 6
PROMPT = ("This is one frame from a hand-tracking video. A cyan skeleton overlay "
          "(21 points + lines) should be drawn on the hand. Answer briefly: "
          "(1) Is a human hand visible? (2) What is the hand doing? "
          "(3) Does the cyan skeleton overlay sit ON the hand, or is it floating "
          "off / missing? One short paragraph.")


def _ollama_describe(image_b64: str) -> str:
    body = json.dumps({
        "model": VISION_MODEL,
        "prompt": PROMPT,
        "images": [image_b64],
        "stream": False,
        "options": {"num_predict": 140},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read()).get("response", "").strip()


def _keyframes_b64(video_path: str, n: int):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total < n:
        idxs = list(range(total))
    else:
        idxs = [int(total * i / n) for i in range(n)]
    out = []
    for fi in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        # downscale a bit to keep the b64 small for the vision model
        h, w = frame.shape[:2]
        scale = 720 / max(w, h) if max(w, h) > 720 else 1.0
        if scale < 1.0:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok2:
            out.append((fi, base64.b64encode(buf).decode()))
    cap.release()
    return out


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python verify_video.py <video>")
        sys.exit(1)
    vpath = sys.argv[1]
    annotated = str(Path(vpath).with_name(Path(vpath).stem + "_annotated.mp4"))

    print("=== 1) MediaPipe numbers + annotated video ===")
    res = validate(vpath, annotated)
    print(f"detected {res['frames_with_hand']}/{res['frames_total']} "
          f"({res['tracking_pct']}%)  fps={res['fps']}")
    if res["metrics"]:
        m = res["metrics"]
        print("Speed=%.1f Acc=%.1f Qual=%.1f composite=%.1f" % (
            m.get("speed", 0), m.get("accuracy", 0), m.get("quality", 0), m.get("composite", 0)))
    print("annotated (YOU watch):", annotated)

    print("\n=== 2) moondream describes key frames (Cipher reads) ===")
    try:
        frames = _keyframes_b64(annotated, N_KEYFRAMES)
    except Exception as exc:
        print("could not read annotated frames:", exc)
        return
    for fi, b64 in frames:
        try:
            desc = _ollama_describe(b64)
        except Exception as exc:
            desc = f"(vision error: {exc})"
        print(f"\n[frame {fi}]")
        print(desc)


if __name__ == "__main__":
    main()
