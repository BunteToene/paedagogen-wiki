#!/usr/bin/env python3
"""Pädagogen-Wiki: baut aus posts/<id>/spec.json die Medien und die post.json.

Aufruf: python3 tools/make_post.py posts/<id>
  - zeichnet Bilder (tools/render.js), bei Reels zusätzlich video.mp4 (ffmpeg, stumm)
  - schreibt post.json mit "approved": false. Freigegeben wird erst nach "Ja, posten".
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def make_video(d: pathlib.Path, n: int, first=2.2, mid=3.0, last=2.6, fade=0.3) -> None:
    durs = [first] + [mid] * (n - 2) + [last] if n > 1 else [first]
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for i, t in enumerate(durs):
        args += ["-loop", "1", "-t", str(t), "-i", str(d / f"scene-{i + 1}.png")]
    total = sum(durs) - fade * (n - 1)
    args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
    fc, prev, off = [], "[0:v]", 0.0
    for i in range(1, n):
        off += durs[i - 1] - fade
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.2f}[v{i}]")
        prev = f"[v{i}]"
    fc.append(f"{prev}format=yuv420p,fps=30[out]")
    args += ["-filter_complex", ";".join(fc), "-map", "[out]", "-map", f"{n}:a", "-c:v", "libx264",
             "-preset", "medium", "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart",
             str(d / "video.mp4")]
    subprocess.run(args, check=True)


def main(rel: str) -> None:
    d = (ROOT / rel).resolve()
    spec = json.loads((d / "spec.json").read_text(encoding="utf-8"))
    subprocess.run(["node", str(ROOT / "tools" / "render.js"), str(d)], check=True)
    post = {k: spec[k] for k in ("type", "publish_at", "caption", "first_comment", "platforms", "youtube") if k in spec}
    post["approved"] = False
    if spec["type"] == "reel":
        n = len(spec["design"]["scenes"])
        make_video(d, n)
        for i in range(n):
            (d / f"scene-{i + 1}.png").unlink()
        post["video"], post["cover"] = "video.mp4", "cover.jpg"
    else:
        slides = sorted(p.name for p in d.glob("slide-*.jpg"))
        alts = spec.get("alts", [])
        post["images"] = [{"file": f, "alt": alts[i] if i < len(alts) else ""} for i, f in enumerate(slides)]
        if len(slides) > 1:
            post["type"] = "carousel"
    (d / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("fertig:", d.name)


if __name__ == "__main__":
    main(sys.argv[1])
