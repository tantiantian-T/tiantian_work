#!/usr/bin/env python3
"""Assemble 9:16 DIY cream-puff short from stills + TTS."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
ASSETS = ROOT / "assets"
OUT = ROOT / "output"
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
W, H, FPS = 1080, 1920, 30


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:8]), "...")
    subprocess.check_call(cmd)


def ffprobe_dur(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def write_wav(path: Path, samples: np.ndarray, sr: int = 44100) -> None:
    import wave
    import struct

    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def make_crunch(path: Path, sr: int = 44100) -> None:
    n = int(sr * 0.22)
    t = np.arange(n) / sr
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1, n)
    # high-passed crackle + a few impulsive clicks
    kernel = np.array([1.0, -1.6, 0.7], dtype=np.float64)
    crackle = np.convolve(noise, kernel, mode="same")
    env = np.exp(-t * 18) * (0.55 + 0.45 * np.exp(-t * 60))
    clicks = np.zeros(n)
    for pos, amp in [(0.008, 0.9), (0.021, 0.55), (0.038, 0.35), (0.06, 0.22)]:
        i = int(pos * sr)
        if i < n:
            clicks[i : i + 40] += amp * np.hanning(40)[: min(40, n - i)]
    sig = (crackle * env * 0.35 + clicks * 0.5) * 0.9
    write_wav(path, sig, sr)


def make_bed(path: Path, seconds: float, sr: int = 44100) -> None:
    n = int(sr * seconds)
    t = np.arange(n) / sr
    # soft major-pentatonic plucks, very low
    freqs = [261.63, 329.63, 392.00, 523.25, 392.00, 329.63]
    sig = np.zeros(n)
    step = 0.46
    for i, f0 in enumerate(freqs * int(seconds / (step * len(freqs)) + 2)):
        start = int(i * step * sr)
        if start >= n:
            break
        length = int(0.42 * sr)
        end = min(n, start + length)
        tt = np.arange(end - start) / sr
        env = np.exp(-tt * 6.5) * (1 - np.exp(-tt * 80))
        tone = np.sin(2 * np.pi * f0 * tt) * 0.55 + np.sin(2 * np.pi * f0 * 2 * tt) * 0.12
        sig[start:end] += tone * env
    # gentle low pad
    pad = 0.08 * np.sin(2 * np.pi * 130.81 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t))
    sig = (sig * 0.045 + pad * 0.03).astype(np.float64)
    fade = min(int(0.4 * sr), n // 8)
    sig[:fade] *= np.linspace(0, 1, fade)
    sig[-fade:] *= np.linspace(1, 0, fade)
    write_wav(path, sig, sr)


def make_silence(path: Path, seconds: float) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            f"{seconds:.3f}",
            "-q:a",
            "4",
            str(path),
        ]
    )


def ken_burns_clip(
    img: Path,
    dur: float,
    caption: str,
    out: Path,
    zoom_in: bool,
    badge: str,
) -> None:
    nframes = max(int(round(dur * FPS)), 1)
    cap_file = out.with_suffix(".caption.txt")
    badge_file = out.with_suffix(".badge.txt")
    cap_file.write_text(caption, encoding="utf-8")
    badge_file.write_text(badge, encoding="utf-8")
    # overscale then slowly pan/zoom via crop expression
    z0, z1 = (1.00, 1.12) if zoom_in else (1.12, 1.00)
    # First scale to cover 1080x1920, then extra 14% for motion
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"scale=iw*1.14:ih*1.14,"
        f"crop={W}:{H}:"
        f"x='(in_w-{W})*(0.15+0.70*t/{dur:.4f})':"
        f"y='(in_h-{H})*{('0.20+0.55*t/' + f'{dur:.4f}') if zoom_in else ('0.75-0.55*t/' + f'{dur:.4f}')}',"
        f"fps={FPS},"
        f"drawtext=fontfile={FONT}:textfile={badge_file}:reload=0:"
        f"fontsize=34:fontcolor=white:borderw=2:bordercolor=0x00000099:"
        f"box=1:boxcolor=0x00000066:boxborderw=14:"
        f"x=(w-text_w)/2:y=72,"
        f"drawtext=fontfile={FONT}:textfile={cap_file}:reload=0:"
        f"fontsize=62:fontcolor=0xFFF6DE:borderw=5:bordercolor=0x3A2414:"
        f"box=1:boxcolor=0x00000055:boxborderw=22:"
        f"x=(w-text_w)/2:y=h-260,"
        f"format=yuv420p"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img),
            "-t",
            f"{dur:.3f}",
            "-vf",
            vf,
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out),
        ]
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="puffvid_"))
    meta = json.loads((ASSETS / "vo_parts" / "meta.json").read_text(encoding="utf-8"))
    durs = [m["dur"] for m in meta]
    gaps = [0.20, 0.22, 0.25, 0.38, 0.22, 0.18, 0.22, 0.22, 0.20, 1.15]
    scene_durs = [d + g for d, g in zip(durs, gaps)]
    # split line 07 audio across mango + berry visuals
    # visual list after combining 04+05 on same product, 07 split:
    visuals = [
        (FRAMES / "01_hook.png", scene_durs[0], "甜品店一个 38？", True, "脆皮泡芙壳 · 开箱即用"),
        (FRAMES / "02_price.png", scene_durs[1], "自己做 才几块钱", False, "脆皮泡芙壳 · 开箱即用"),
        (FRAMES / "03_product_tray.png", scene_durs[2], "最难的壳 我们烤好了", True, "脆皮泡芙壳 · 开箱即用"),
        (FRAMES / "04_snap.png", scene_durs[3], "你听这声音  咔", False, "脆皮泡芙壳 · 开箱即用"),
        (FRAMES / "04_snap.png", scene_durs[4], "一掰全空  能塞超多奶油", True, "脆皮泡芙壳 · 开箱即用"),
        (FRAMES / "05_pipe.png", scene_durs[5], "打开就能用", False, "5分钟出甜品店同款"),
        (FRAMES / "06_mango.png", scene_durs[6] * 0.48, "芒果的", True, "5分钟出甜品店同款"),
        (FRAMES / "07_berry.png", scene_durs[6] * 0.52, "草莓的 · 青提的", False, "5分钟出甜品店同款"),
        (FRAMES / "08_final.png", scene_durs[7], "壳够脆 · 心够空 · 够高级", True, "你负责好看  我负责烤壳"),
        (FRAMES / "09_bite.png", scene_durs[8], "你负责好看", False, "你负责好看  我负责烤壳"),
        (FRAMES / "10_cta.png", scene_durs[9], "评论区扣「要」  链接给你", True, "脆皮泡芙壳  现在下单"),
    ]

    clips = []
    for i, (img, dur, cap, zin, badge) in enumerate(visuals, 1):
        clip = tmp / f"v{i:02d}.mp4"
        ken_burns_clip(img, dur, cap, clip, zin, badge)
        clips.append(clip)

    concat_list = tmp / "vlist.txt"
    concat_list.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
    video_path = tmp / "video.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(video_path),
        ]
    )

    # audio: vo parts + silences
    audio_parts = []
    for i, (m, gap) in enumerate(zip(meta, gaps), 1):
        audio_parts.append(ASSETS / "vo_parts" / f"{i:02d}.mp3")
        sil = tmp / f"sil{i:02d}.mp3"
        make_silence(sil, gap)
        audio_parts.append(sil)

    alist = tmp / "alist.txt"
    # re-encode parts to wav first for clean concat
    wavs = []
    for i, p in enumerate(audio_parts):
        w = tmp / f"a{i:03d}.wav"
        run(["ffmpeg", "-y", "-i", str(p), "-ar", "44100", "-ac", "1", str(w)])
        wavs.append(w)
    alist.write_text("".join(f"file '{w}'\n" for w in wavs), encoding="utf-8")
    vo_wav = tmp / "vo.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(alist),
            "-c",
            "pcm_s16le",
            str(vo_wav),
        ]
    )

    crunch = tmp / "crunch.wav"
    make_crunch(crunch)
    # place crunch near the "咔" — after lines 1-3 + small offset into line 4
    crunch_at = sum(scene_durs[:3]) + durs[3] * 0.62

    vdur = ffprobe_dur(video_path)
    bed = tmp / "bed.wav"
    make_bed(bed, vdur + 0.3)

    mixed = tmp / "mixed.m4a"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(vo_wav),
            "-i",
            str(bed),
            "-i",
            str(crunch),
            "-filter_complex",
            f"[1:a]volume=0.22[bed];"
            f"[2:a]adelay={int(crunch_at*1000)}|{int(crunch_at*1000)},volume=1.15[cr];"
            f"[0:a]volume=1.25[vo];"
            f"[vo][bed][cr]amix=inputs=3:duration=first:dropout_transition=0,"
            f"loudnorm=I=-14:TP=-1.5:LRA=11[a]",
            "-map",
            "[a]",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(mixed),
        ]
    )

    final = OUT / "脆皮泡芙壳_DIY短视频.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(mixed),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            "-pix_fmt",
            "yuv420p",
            str(final),
        ]
    )
    print("DONE", final, "duration", ffprobe_dur(final))


if __name__ == "__main__":
    main()
