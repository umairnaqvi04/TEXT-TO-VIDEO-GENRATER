"""
Text -> Video (local, free). Run:  streamlit run app.py
Script format: one scene per line ->  visual prompt | narration text
Pipeline: free AI image (Pollinations) + free voice (edge-tts) + subtitles + zoom effect -> MP4 (ffmpeg)
"""
import asyncio, os, subprocess, textwrap, time, urllib.parse, shutil
from pathlib import Path

import arabic_reshaper
import edge_tts
import imageio_ffmpeg
import requests
import streamlit as st
from mutagen.mp3 import MP3
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = Path("output")

VOICES = {
    "Urdu - Asad (male)": "ur-PK-AsadNeural",
    "Urdu - Uzma (female)": "ur-PK-UzmaNeural",
    "Hindi - Madhur (male)": "hi-IN-MadhurNeural",
    "Hindi - Swara (female)": "hi-IN-SwaraNeural",
    "English - Guy (male)": "en-US-GuyNeural",
    "English - Jenny (female)": "en-US-JennyNeural",
}
RATIOS = {"16:9 (YouTube)": (1280, 720), "9:16 (Shorts)": (720, 1280)}


def get_font(size):
    for f in ["NotoNastaliqUrdu-Regular.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default(size)


def placeholder(text, size, path):
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        c = int(40 + 90 * y / h)
        d.line([(0, y), (w, y)], fill=(c, 60, 140 - c // 3))
    img.save(path)


def make_image(prompt, size, seed, path, use_ai):
    if use_ai:
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
               + f"?width={size[0]}&height={size[1]}&seed={seed}&nologo=true")
        for _ in range(3):
            try:
                r = requests.get(url, timeout=120)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    path.write_bytes(r.content)
                    Image.open(path).convert("RGB").resize(size).save(path)
                    return True
            except Exception:
                pass
            time.sleep(4)
    placeholder(prompt, size, path)
    return False


def shape(t):
    if any("\u0600" <= c <= "\u06ff" for c in t):
        return get_display(arabic_reshaper.reshape(t))
    return t


def make_subtitle(text, size, path):
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fs = max(26, w // 28)
    font = get_font(fs)
    lines = textwrap.wrap(text, width=max(18, int(w / (fs * 0.55))))[:4]
    lh = int(fs * 1.35)
    box_h = lh * len(lines) + 24
    y0 = h - box_h - int(h * 0.05)
    d.rounded_rectangle([int(w * 0.05), y0, int(w * 0.95), y0 + box_h], 18, fill=(0, 0, 0, 150))
    for i, ln in enumerate(lines):
        ln = shape(ln)
        tw = d.textlength(ln, font=font)
        d.text(((w - tw) / 2, y0 + 12 + i * lh), ln, font=font, fill=(255, 255, 255, 255))
    img.save(path)


async def tts(text, voice, rate, path):
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def render_scene(img, sub, audio, dur, size, fps, out, zoom):
    w, h = size
    frames = int(dur * fps) + 1
    z = "min(zoom+0.0007,1.15)" if zoom else "1"
    flt = (f"[0:v]scale={w*2}:{h*2},zoompan=z='{z}':d={frames}:s={w}x{h}:fps={fps}"
           f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[bg];"
           f"[bg][1:v]overlay=0:0,format=yuv420p[v]")
    cmd = [FFMPEG, "-y", "-i", str(img), "-i", str(sub), "-i", str(audio),
           "-filter_complex", flt, "-map", "[v]", "-map", "2:a", "-t", f"{dur:.2f}",
           "-af", "apad", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-ar", "44100", "-ac", "2",
           "-r", str(fps), str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


def parse(script):
    scenes = []
    for ln in script.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "|" in ln:
            v, n = ln.split("|", 1)
        else:
            v, n = ln, ln
        scenes.append((v.strip(), n.strip()))
    return scenes


import hashlib

st.set_page_config(page_title="Text to Video", layout="wide")
st.title("Text to Video (Local)")
st.caption("Script paste karein, video khud ban jayegi. Har line = ek scene:  visual prompt | narration")

with st.sidebar:
    auto = st.checkbox("Auto-generate (paste karte hi video banao)", True)
    ratio = st.selectbox("Aspect ratio", list(RATIOS))
    voice = st.selectbox("Voice", list(VOICES))
    speed = st.slider("Voice speed (%)", -30, 30, 0)
    fps = st.selectbox("FPS", [24, 30], index=0)
    style = st.text_area("Style / character line (har scene ke shuru mein lagegi)",
                         "3D Pixar-style animation, cinematic lighting, Punjab village, mud houses. Characters: Aloo, "
                         "14-year-old boy, short black hair, brown shalwar kameez, red scarf; Bhindi, 11-year-old girl, "
                         "long braid, green dupatta; Dada Gobi, 70-year-old grandfather, white beard, white turban, "
                         "walking stick; Seth Kaddu, heavy rich landlord, big moustache, cream shalwar kameez, gold "
                         "watch; Mirchi, 12-year-old girl, red dress, two short braids.",
                         height=150)
    use_ai = st.checkbox("AI images (Pollinations, free, internet chahiye)", True)
    zoom = st.checkbox("Zoom effect", True)
    min_len = st.slider("Minimum scene length (sec)", 4, 12, 10)
    base_seed = st.number_input("Seed", 0, 99999, 7)

if "script" not in st.session_state:
    st.session_state.script = ""
if "last_hash" not in st.session_state:
    st.session_state.last_hash = ""
if "final" not in st.session_state:
    st.session_state.final = None

c1, c2 = st.columns(2)
if c1.button("Sample 12-min story load karein"):
    f = Path("story_12min.txt")
    st.session_state.script = f.read_text(encoding="utf-8") if f.exists() else ""
    st.session_state.last_hash = ""
if c2.button("Script saaf karein"):
    st.session_state.script = ""
    st.session_state.last_hash = ""
    st.session_state.final = None

script = st.text_area("Script (yahan naya script paste karein, phir Ctrl+Enter ya bahar tap karein)",
                      key="script", height=320)


def generate(scenes):
    size = RATIOS[ratio]
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    bar, status = st.progress(0.0), st.empty()
    segs = []
    for i, (vis, nar) in enumerate(scenes, 1):
        status.write(f"Scene {i}/{len(scenes)} ban raha hai...")
        img, sub, aud, seg = (OUT / f"{i}.png", OUT / f"{i}_sub.png", OUT / f"{i}.mp3", OUT / f"{i}.mp4")
        ok = make_image(f"{style}. {vis}", size, base_seed + i, img, use_ai)
        if use_ai and not ok:
            st.warning(f"Scene {i}: AI image nahi mili, placeholder lagaya.")
        make_subtitle(nar, size, sub)
        asyncio.run(tts(nar, VOICES[voice], f"{speed:+d}%", aud))
        dur = max(MP3(str(aud)).info.length + 0.4, float(min_len))
        render_scene(img, sub, aud, dur, size, fps, seg, zoom)
        segs.append(seg)
        bar.progress(i / (len(scenes) + 1))
    status.write("Clips jor raha hoon...")
    lst = OUT / "list.txt"
    lst.write_text("\n".join(f"file '{s.resolve().as_posix()}'" for s in segs), encoding="utf-8")
    final = OUT / "final.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final)],
                   check=True, capture_output=True)
    bar.progress(1.0)
    status.write("Video tayyar!")
    st.session_state.final = str(final)


scenes = parse(script)
h = hashlib.md5(script.strip().encode("utf-8")).hexdigest() if scenes else ""
manual = st.button("Generate Video", type="primary")
if scenes and (manual or (auto and h != st.session_state.last_hash)):
    st.session_state.last_hash = h
    try:
        generate(scenes)
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.final and Path(st.session_state.final).exists():
    st.video(st.session_state.final)
    st.download_button("Download MP4", Path(st.session_state.final).read_bytes(), "video.mp4", "video/mp4")
