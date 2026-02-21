import yt_dlp
import os
import uuid
import subprocess
import shutil
import re
import traceback
from datetime import timedelta
import static_ffmpeg

# Setup FFmpeg Paths
try:
    if os.name == 'nt':
        static_ffmpeg.add_paths()
        ffmpeg_execs = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        FFMPEG_EXE = ffmpeg_execs[0]
        FFPROBE = ffmpeg_execs[1]
    else:
        FFMPEG_EXE = "ffmpeg"
        FFPROBE = "ffprobe"
except:
    FFMPEG_EXE = "ffmpeg"
    FFPROBE = "ffprobe"

def time_to_seconds(t_str):
    if not t_str: return 0.0
    try:
        parts = list(map(float, str(t_str).split(":")))
        if len(parts) == 1: return parts[0]
        if len(parts) == 2: return parts[0]*60 + parts[1]
        if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
        return 0.0
    except:
        return 0.0

def get_video_info(url):
    """NO-FAIL METADATA FETCH ENGINE"""
    if "youtu.be/" in url:
        v_id = url.split("youtu.be/")[1].split("?")[0]
        url = f"https://www.youtube.com/watch?v={v_id}"

    cookie_file = "youtube_cookies.txt"
    if not os.path.exists(cookie_file) and os.path.exists("youtube_cookies.txt.txt"):
        cookie_file = "youtube_cookies.txt.txt"

    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'no_playlist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    if os.path.exists(cookie_file):
        common_opts['cookiefile'] = cookie_file

    # STEP 1: Try full extraction
    with yt_dlp.YoutubeDL(common_opts) as ydl:
        try:
            print(f"RAILWAY: Phase 1 Fetch for {url}")
            info = ydl.extract_info(url, download=False)
            
            if info:
                if 'entries' in info: info = info['entries'][0]
                formats = info.get("formats", [])
                heights = sorted(list(set([f.get("height") for f in formats if f.get("height")])))
                if not heights: heights = [360, 480, 720, 1080]
                
                return {
                    "id": info.get("id"),
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "duration_str": str(timedelta(seconds=info.get("duration") or 0)),
                    "avail_heights": heights
                }
        except Exception as e:
            print(f"RAILWAY Phase 1 Failed (Expected): {str(e)}")

    # STEP 2: Fallback to Flat Extraction (Bypasses format blocks)
    common_opts['extract_flat'] = True
    with yt_dlp.YoutubeDL(common_opts) as ydl:
        try:
            print(f"RAILWAY: Phase 2 (Flat) Fetch for {url}")
            info = ydl.extract_info(url, download=False)
            if info:
                return {
                    "id": info.get("id"),
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail") or f"https://i.ytimg.com/vi/{info.get('id')}/hqdefault.jpg",
                    "duration": info.get("duration"),
                    "duration_str": str(timedelta(seconds=info.get("duration") or 0)),
                    "avail_heights": [360, 480, 720, 1080] # Fallback heights
                }
        except Exception as e:
            print(f"RAILWAY Phase 2 Failed: {str(e)}")
            return {"error": "YouTube is blocking connection. Try again."}

def process_video(url, mode='trim', start_time=None, end_time=None, quality_height=720):
    """ULTRA-TURBO INSTANT ENGINE"""
    s_sec = time_to_seconds(start_time)
    e_sec = time_to_seconds(end_time)
    duration_sec = e_sec - s_sec

    ydl_opts = {
        'format': f'bestvideo[height<={quality_height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'nocheckcertificate': True,
    }
    
    cookie_file = "youtube_cookies.txt"
    if not os.path.exists(cookie_file) and os.path.exists("youtube_cookies.txt.txt"):
        cookie_file = "youtube_cookies.txt.txt"
    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get('title', 'StreamTrim_Video')
            clean_title = re.sub(r'[^\w\s-]', '', raw_title).strip().replace(' ', '_')
            final_output = os.path.abspath(os.path.join("downloads", f"{clean_title}_{uuid.uuid4().hex[:4]}.mp4"))
            
            cmd = [FFMPEG_EXE, "-y", "-hide_banner", "-loglevel", "error"]
            req_formats = info.get('requested_formats')
            
            if req_formats and len(req_formats) >= 2:
                v_url, a_url = req_formats[0]['url'], req_formats[1]['url']
                if mode == 'trim':
                    cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", v_url])
                    cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", a_url])
                else:
                    cmd.extend(["-i", v_url, "-i", a_url])
            else:
                stream_url = info['url']
                if mode == 'trim':
                    cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", stream_url])
                else:
                    cmd.extend(["-i", stream_url])

            cmd.extend(["-c", "copy", "-movflags", "faststart"])
            cmd.append(final_output)
            subprocess.run(cmd, check=True)
            return final_output if os.path.exists(final_output) else {"error": "Failed to save file."}

    except Exception as e:
        print(f"RAILWAY PROCESS ERROR: {str(e)}")
        return {"error": f"Download Fail: YouTube is restricting this video."}
