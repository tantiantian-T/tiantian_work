#!/usr/bin/env python3
"""Compose a 9:16 DIY crispy cream-puff shell marketing short."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
OUTPUT = ROOT / "output"
AUDIO = OUTPUT / "audio"
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
VOICE = "zh-CN-XiaoyiNeural"
W, H = 1080, 1920
FPS = 30

# (filename, spoken text, on-screen subtitle, duration seconds)
SEGMENTS = [
    ("frame01_hook.jpg", "谁说做泡芙一定要烤箱？", "谁说做泡芙一定要烤箱？", 3.2),
    (
        "frame02_product.jpg",
        "这个脆皮壳，开箱就能用！金黄酥脆，专业款脆顶。",
        "开箱即用 · 金黄脆皮壳",
        4.2,
    ),
    (
        "frame08_texture.jpg",
        "听这口感，咖嚓一声就懂了。",
        "咖嚓脆顶 · 专业质感",
        3.0,
    ),
    (
        "frame03_hollow.jpg",
        "掰开全是空心，专门留给奶油的！",
        "空心大空间 · 奶油随便灌",
        3.8,
    ),
    (
        "frame04_fill.jpg",
        "挤奶油、放水果，三分钟出片。",
        "挤奶油 · 三分钟出片",
        3.6,
    ),
    (
        "frame05_decorate.jpg",
        "芒果、草莓、青提、杨梅，随心DIY。",
        "水果随心配 · 好看随便出",
        4.0,
    ),
    (
        "frame06_result.jpg",
        "咖啡店同款颜值，在家也能摆一盘！",
        "咖啡店同款 · 在家也能摆一盘",
        3.8,
    ),
    (
        "frame07_cta.jpg",
        "脆皮泡芙壳现货直发，你只负责好看。点下方，壳先囤起来！",
        "现货直发 · 你只负责好看 ↓",
        5.0,
    ),
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:8]), "..." if len(cmd) > 8 else "")
    subprocess.run(cmd, check=True)


async def synth_voice() -> Path:
    AUDIO.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for i, (_, text, _, duration) in enumerate(SEGMENTS):
        out = AUDIO / f"seg_{i:02d}.mp3"
        # Slightly faster for short-video energy
        communicate = edge_tts.Communicate(text, VOICE, rate="+8%")
        await communicate.save(str(out))
        # Pad/trim to target duration with silence so picture sync stays clean
        padded = AUDIO / f"seg_{i:02d}_pad.wav"
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(out),
                "-af",
                f"apad=pad_dur={duration},atrim=0:{duration},loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                "44100",
                "-ac",
                "1",
                str(padded),
            ]
        )
        parts.append(padded)

    concat_list = AUDIO / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in parts) + "\n")
    voice = OUTPUT / "voiceover.wav"
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
            str(voice),
        ]
    )
    return voice


def make_ass() -> Path:
    ass = OUTPUT / "subs.ass"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,WenQuanYi Micro Hei,72,&H00FFFFFF,&H000000FF,&H001A0A00,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,220,1
Style: Cap,WenQuanYi Micro Hei,58,&H00FFFFFF,&H000000FF,&H00204080,&H90000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    t = 0.0
    for i, (_, _, sub, dur) in enumerate(SEGMENTS):
        start = t
        end = t + dur - 0.08
        style = "Hook" if i == 0 or i == len(SEGMENTS) - 1 else "Cap"
        lines.append(
            f"Dialogue: 0,{fmt(start)},{fmt(end)},{style},,0,0,0,,{ass_escape(sub)}"
        )
        t += dur
    ass.write_text("\n".join(lines), encoding="utf-8")
    return ass


def fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def make_visual_clips() -> list[Path]:
    clips: list[Path] = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for i, (fname, _, _, duration) in enumerate(SEGMENTS):
        src = FRAMES / fname
        frames = max(int(duration * FPS), 1)
        # Alternate subtle Ken Burns zoom directions
        if i % 2 == 0:
            zoom = f"zoompan=z='min(1.12,1+0.0012*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
        else:
            zoom = f"zoompan=z='if(eq(on,1),1.12,max(1.0,1.12-0.0012*on))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
        out = OUTPUT / f"clip_{i:02d}.mp4"
        vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"{zoom},"
            f"fps={FPS},format=yuv420p"
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(src),
                "-vf",
                vf,
                "-t",
                f"{duration:.2f}",
                "-an",
                "-pix_fmt",
                "yuv420p",
                str(out),
            ]
        )
        clips.append(out)
    return clips


def concat_clips(clips: list[Path]) -> Path:
    lst = OUTPUT / "clips.txt"
    lst.write_text("\n".join(f"file '{c.resolve()}'" for c in clips) + "\n")
    silent = OUTPUT / "picture_silent.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(silent),
        ]
    )
    return silent


def mux(picture: Path, voice: Path, ass: Path) -> Path:
    final = OUTPUT / "脆皮泡芙壳_DIY带货短视频.mp4"
    # Escape path for ass filter
    ass_path = str(ass).replace("\\", "/").replace(":", "\\:")
    # Soft light music bed from ffmpeg sine + noise is too harsh; keep voice-forward with gentle high-pass
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(picture),
            "-i",
            str(voice),
            "-filter_complex",
            f"[0:v]ass={ass_path}[v];[1:a]aformat=sample_rates=44100:channel_layouts=mono[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final),
        ]
    )
    return final


async def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    voice = await synth_voice()
    ass = make_ass()
    clips = make_visual_clips()
    picture = concat_clips(clips)
    final = mux(picture, voice, ass)
    # Also copy to artifacts for easy download
    artifact = Path("/opt/cursor/artifacts") / final.name
    run(["cp", str(final), str(artifact)])
    print(f"DONE: {final}")
    print(f"ARTIFACT: {artifact}")


if __name__ == "__main__":
    asyncio.run(main())
