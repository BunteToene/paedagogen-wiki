#!/usr/bin/env python3
"""Macht aus den Karussell-Bildern eines Posts ein YouTube-Short (1080x1920, stumm).
Aufruf: python3 tools/short_from_slides.py posts/<id> <ausgabe.mp4>
"""
import pathlib
import subprocess
import sys

d = pathlib.Path(sys.argv[1])
out = sys.argv[2]
slides = sorted(d.glob("slide-*.jpg"))
durs = [2.4] + [3.6] * (len(slides) - 2) + [2.8]
fade = 0.3
args = ["ffmpeg", "-y", "-loglevel", "error"]
for s, t in zip(slides, durs):
    args += ["-loop", "1", "-t", str(t), "-i", str(s)]
total = sum(durs) - fade * (len(slides) - 1)
args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
fc = [f"[{i}:v]scale=1080:1350,pad=1080:1920:0:285:color=0xFBF7EF,setsar=1[p{i}]" for i in range(len(slides))]
prev, off = "[p0]", 0.0
for i in range(1, len(slides)):
    off += durs[i - 1] - fade
    fc.append(f"{prev}[p{i}]xfade=transition=fade:duration={fade}:offset={off:.2f}[v{i}]")
    prev = f"[v{i}]"
fc.append(f"{prev}format=yuv420p,fps=30[out]")
args += ["-filter_complex", ";".join(fc), "-map", "[out]", "-map", f"{len(slides)}:a", "-c:v", "libx264",
         "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart", out]
subprocess.run(args, check=True)
