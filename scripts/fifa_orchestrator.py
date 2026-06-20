import json
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add yt-automation pipeline to path to import components
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))

# Load .env variables so Groq/YouTube API works
from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env")

# Switch Groq model to avoid the 70b rate limit
os.environ["GROQ_MODEL"] = "llama-3.1-8b-instant"

from pipeline.youtube_upload import upload_short
from pipeline.channel_presets import get_preset
from pipeline.groq_script import generate_short_pack
from pipeline.edge_tts_synth import synthesize_full
from pipeline.captions import build_srt
from pipeline.render_short import render_video_background_short

YOUTUBE_SHORT_GEN_DIR = os.environ.get("YOUTUBE_SHORT_GEN_DIR", "/home/sp/Public/my_project/opensource-video/youtube_short_generator/AI-Youtube-Shorts-Generator")

# Determine python/yt-dlp commands based on whether we're in a GitHub Action or local
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"

if IN_GITHUB_ACTIONS:
    YT_DLP_PATH = "yt-dlp" # Global install in CI
    GENERATE_CMD = "python main.py"
else:
    YT_DLP_PATH = os.path.join(YOUTUBE_SHORT_GEN_DIR, "venv", "bin", "yt-dlp")
    GENERATE_CMD = "source venv/bin/activate && python main.py"

def search_fifa_video():
    print("Searching for FIFA videos...")
    if IN_GITHUB_ACTIONS:
        cmd = [sys.executable, "-m", "yt_dlp", "ytsearch20:fifa 2026 highlights", "-J"]
    else:
        cmd = [YT_DLP_PATH, "ytsearch20:fifa 2026 highlights", "-J"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        playlist = json.loads(result.stdout)
        entries = playlist.get("entries", [])
        for data in entries:
            duration = data.get("duration", 0)
            if 180 <= duration <= 3600: # 3 minutes to 60 minutes
                video_url = data.get("webpage_url") or f"https://www.youtube.com/watch?v={data['id']}"
                print(f"Found suitable video: {video_url} (Duration: {duration}s)")
                return video_url
    except Exception as e:
        print(f"Error parsing yt-dlp output: {e}")
        print(f"STDOUT: {result.stdout[:500]}")
        print(f"STDERR: {result.stderr}")
    raise RuntimeError("No suitable FIFA video found. Ensure yt-dlp is not being blocked.")

def generate_shorts(video_url):
    print(f"Generating 4 clips from {video_url}...")
    cmd = [
        "bash", "-c",
        f"{GENERATE_CMD} '{video_url}' --num-clips 4 --aspect-ratio 9:16 --mode local --output-json result.json"
    ]
    import time
    for attempt in range(5):
        try:
            subprocess.run(cmd, cwd=YOUTUBE_SHORT_GEN_DIR, check=True)
            return
        except subprocess.CalledProcessError as e:
            print(f"Generation failed on attempt {attempt+1}: {e}")
            time.sleep(10)
    raise RuntimeError("Failed to generate clips after 5 attempts.")

def process_and_upload_shorts():
    result_path = os.path.join(YOUTUBE_SHORT_GEN_DIR, "result.json")
    if not os.path.exists(result_path):
        raise FileNotFoundError(f"Result JSON not found: {result_path}")
        
    with open(result_path, "r") as f:
        data = json.load(f)
        
    shorts = data.get("shorts", [])
    if not shorts:
        raise ValueError("No shorts were generated!")
        
    print(f"Found {len(shorts)} raw FIFA clips. Starting yt-automation pipeline overlay...")
    
    # We use the 'fifa_2026' preset for the yt-automation flow
    preset = get_preset("fifa_2026")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "runs" / f"fifa_overlay_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    for i, short in enumerate(shorts, 1):
        clip_path = short.get("clip_url")
        if not clip_path or not os.path.exists(os.path.join(YOUTUBE_SHORT_GEN_DIR, clip_path)):
            print(f"Raw clip file missing for short {i}, skipping.")
            continue
            
        raw_clip = Path(YOUTUBE_SHORT_GEN_DIR) / clip_path
        
        print(f"\n--- Processing Clip {i} ---")
        
        # 1. Groq Script
        print("1. Generating new script via Groq...")
        context_hint = f"Rewrite this specific moment into an engaging, detailed 150-word story script for a YouTube short: {short.get('title')}. Details: {short.get('hook_sentence')}. {short.get('virality_reason')}"
        pack = None
        for attempt in range(3):
            try:
                pack = generate_short_pack(preset, topic_hint=context_hint, channel_id="fifa_2026")
                break
            except Exception as e:
                print(f"Groq script generation failed (attempt {attempt+1}): {e}")
        if not pack:
            print("Skipping short due to persistent Groq errors.")
            continue
        
        title = pack["youtube_title"] + " #shorts #fifa"
        narration = pack["full_narration"]
        
        # 2. Edge TTS
        audio_path = run_dir / f"voiceover_{i}.mp3"
        print("2. Synthesizing Edge TTS...")
        total_dur, timings = synthesize_full(narration, audio_path, voice=preset.get("tts_voice") or os.environ.get("EDGE_TTS_VOICE"))
        
        # 3. Captions
        srt_path = run_dir / f"captions_{i}.srt"
        print("3. Building SRT captions...")
        build_srt(timings, srt_path, total_dur)
        
        # 4. Render
        final_video_path = run_dir / f"final_short_{i}.mp4"
        print("4. Rendering final MP4 with FIFA background + TTS + Captions...")
        render_video_background_short(
            bg_video_path=raw_clip,
            total_duration=total_dur,
            audio_path=audio_path,
            srt_path=srt_path,
            out_video=final_video_path,
            font_file=preset.get("caption_font", "CreepsterCaps.ttf"),
            font_name=preset.get("caption_font_name", "Creepster")
        )
        
        # 5. Upload
        print(f"5. Uploading: {title}")
        try:
            video_id = upload_short(
                video_path=final_video_path,
                title=title,
                description=pack.get("youtube_description", ""),
                privacy_status="private",
                category_id="17",
                refresh_token_env=preset.get("yt_token_env") or "YT_REFRESH_TOKEN"
            )
            print(f"Successfully uploaded! Video ID: {video_id}")
            print(f"Link: https://youtube.com/shorts/{video_id}")
        except Exception as e:
            print(f"Failed to upload short {i}: {e}")

if __name__ == "__main__":
    try:
        url = search_fifa_video()
        generate_shorts(url)
        process_and_upload_shorts()
        print("Ultimate goal pipeline completed successfully using video highlights!")
    except Exception as e:
        print(f"Video scraping failed (likely YouTube IP block): {e}")
        print("Gracefully falling back to the robust Image Slideshow engine...")
        import sys
        from pathlib import Path
        REPO_ROOT = Path(__file__).resolve().parent.parent
        sys.path.append(str(REPO_ROOT / "scripts"))
        try:
            import run_slideshow
            run_slideshow.main()
            print("Ultimate goal pipeline completed successfully using slideshow fallback!")
        except Exception as fallback_err:
            print(f"Fallback also failed: {fallback_err}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
