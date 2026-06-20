#!/usr/bin/env python3
"""
Fully automated Web-Image Slideshow YouTube Short pipeline.

Generates:
  Groq → narration + visual search queries
  Web Scraper → fetches DuckDuckGo images
  Edge TTS → audio voiceover
  Captions → SRT
  FFmpeg → slideshow with Ken Burns zoom, xfade stitch and overlay captions
  YouTube/Insta upload (optional)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output so Unicode/emoji prints work on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env")

from pipeline.captions import build_srt
from pipeline.channel_presets import get_preset, list_channel_ids
from pipeline.edge_tts_synth import synthesize_full
from pipeline.groq_script import generate_short_pack
from pipeline.story_history import save_title
from pipeline.web_images import fetch_web_image
from pipeline.render_short import render_vertical_short

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate Slideshow YouTube Short.")
    ap.add_argument("--channel", default="fifa_2026", choices=list_channel_ids() if callable(list_channel_ids) else [])
    ap.add_argument("--topic", default="", help="Optional topic hint for Groq.")
    ap.add_argument("--upload", action="store_true", help="Upload to YouTube after render.")
    ap.add_argument("--instagram", action="store_true", help="Upload to Instagram Reels after render.")
    ap.add_argument("--facebook", action="store_true", help="Upload to Facebook Page Reels after render.")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    # Get preset and override segment_count to 5 (good for ~60s short)
    preset = get_preset(args.channel)
    preset = dict(preset)
    preset["segment_count"] = 25
    preset["min_words"] = 100

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "runs" / f"{args.channel}_slideshow_{ts}"
    img_dir = run_dir / "images"
    
    img_dir.mkdir(parents=True, exist_ok=True)

    # 1. Groq Script Generation
    topic_hint = args.topic.strip() or None
    fifa_context = None
    if not topic_hint and preset.get("topic_rotation") == "fifa_2026":
        try:
            from pipeline.fifa_2026 import pick_fifa_topic
            topic_hint, fifa_context = pick_fifa_topic()
            print(f"[FIFA 2026] Content angle selected: {topic_hint!r}")
        except ImportError:
            pass

    print("\n① Groq: generating script with 25 image segments...")
    pack = generate_short_pack(
        preset, topic_hint=topic_hint, channel_id=args.channel,
        extra_context=fifa_context,
    )
    (run_dir / "script.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")

    title = pack["youtube_title"]
    narration = pack["full_narration"]
    search_queries = pack.get("visual_search_queries", [])

    print(f"   Title: {title}")
    print(f"   Narration: {len(narration.split())} words")
    print(f"   Visual queries generated: {len(search_queries)}")

    # 2. Synthesize TTS
    audio_path = run_dir / "voiceover.mp3"
    voice = preset.get("tts_voice") or os.environ.get("EDGE_TTS_VOICE")
    print(f"\n② Edge TTS ({voice or 'default'})...")
    total_dur, sentence_timings = synthesize_full(narration, audio_path, voice=voice)
    print(f"   Audio: {total_dur:.1f}s ({len(sentence_timings)} sentences)")

    # 3. Create captions SRT
    srt_path = run_dir / "captions.srt"
    print("\n③ Captions (SRT)...")
    build_srt(sentence_timings, srt_path, total_dur)

    # 4. Fetch Images
    print(f"\n④ Fetching {len(search_queries)} web images...")
    image_paths = []
    
    for i, query in enumerate(search_queries, 1):
        # Force strict football context so DuckDuckGo doesn't return vague/generic images
        strict_query = f"{query} FIFA World Cup football match"
        print(f"   [Image {i}/{len(search_queries)}] Searching: {strict_query}")
        out_path = img_dir / f"img_{i:02d}.jpg"
        status, detail = fetch_web_image(strict_query, out_path)
        if status == "ok":
            print(f"      Saved: {detail}")
            image_paths.append(out_path)
        else:
            print(f"      Failed to fetch image: {detail}")
            # we can fallback or duplicate the last image if it fails
            if len(image_paths) > 0:
                print("      Falling back to previous image...")
                fallback = img_dir / f"img_{i:02d}_fallback.jpg"
                shutil.copyfile(image_paths[-1], fallback)
                image_paths.append(fallback)

    if not image_paths:
        print("ERROR: All image fetches failed.")
        sys.exit(1)

    # 5. Render final video
    print("\n⑤ Rendering final slideshow with Ken Burns effects & captions...")
    font_file = preset.get("caption_font", "CreepsterCaps.ttf")
    font_name = preset.get("caption_font_name", "Creepster")
    
    out_video = run_dir / "short.mp4"
    render_vertical_short(
        image_paths=image_paths,
        total_duration=total_dur,
        audio_path=audio_path,
        srt_path=srt_path,
        out_video=out_video,
        font_file=font_file,
        font_name=font_name,
    )
    print(f"\n[OK] Video successfully rendered: {out_video}")

    # 6. Upload to YouTube (optional)
    if args.upload:
        from pipeline.youtube_upload import upload_short
        yt_token_env = preset.get("yt_token_env") or "YT_REFRESH_TOKEN"
        print(f"\n⑥ YouTube: uploading ({yt_token_env})...")
        try:
            vid = upload_short(
                out_video, title, pack.get("youtube_description", ""),
                privacy_status=args.privacy,
                refresh_token_env=yt_token_env,
            )
            print(f"   Uploaded! https://www.youtube.com/shorts/{vid}")
        except Exception as e:
            print(f"   YouTube upload failed: {e}")

    # 6.5 Upload to Instagram Reels (optional)
    if args.instagram:
        from pipeline.instagram_upload import publish_instagram_reel
        print("\n[Instagram] Uploading to Instagram Reels...")
        try:
            caption = pack.get("youtube_description", "")
            media_id = publish_instagram_reel(out_video, caption)
            print(f"   [Instagram] Uploaded Reel! Media ID: {media_id}")
        except Exception as e:
            print(f"   [Instagram] Upload failed: {e}")

    # 6.6 Upload to Facebook Page Reels (optional)
    if args.facebook:
        from pipeline.instagram_upload import publish_facebook_reel
        print("\n[Facebook] Uploading to Facebook Page Reels...")
        try:
            caption = pack.get("youtube_description", "")
            video_id = publish_facebook_reel(out_video, caption)
            print(f"   [Facebook] Uploaded Reel! Video ID: {video_id}")
        except Exception as e:
            print(f"   [Facebook] Upload failed: {e}")

    # Save to history
    summary = " ".join(narration.split()[:25]) + "…"
    save_title(args.channel, title, summary)

    print("\n✓ Slideshow Pipeline Complete.")

if __name__ == "__main__":
    main()
