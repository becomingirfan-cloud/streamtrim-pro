import yt_dlp
import os
import uuid
import subprocess
import shutil
import re
import requests
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
    """ULTIMATE NO-FAIL FETCH (Using OEmbed + yt-dlp Fallback)"""
    v_id = None
    if "youtu.be/" in url:
        v_id = url.split("youtu.be/")[1].split("?")[0]
    elif "v=" in url:
        v_id = url.split("v=")[1].split("&")[0]
    
    if not v_id:
        return {"error": "Invalid YouTube URL"}

    clean_url = f"https://www.youtube.com/watch?v={v_id}"

    # METHOD 1: Use YouTube's Public OEmbed (Unblockable for Basic Info)
    try:
        print(f"RAILWAY: Method 1 (OEmbed) for {v_id}")
        r = requests.get(f"https://www.youtube.com/oembed?url={clean_url}&format=json", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                "id": v_id,
                "title": data.get("title", f"Video_{v_id}"),
                "thumbnail": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg",
                "duration": 0, # OEmbed doesn't give duration but it gets you past 'Analyzing'
                "duration_str": "Unknown",
                "avail_heights": [360, 480, 720, 1080],
                "oembed": True
            }
    except Exception as e:
        print(f"OEmbed Failed: {e}")

    # METHOD 2: Strict yt-dlp with no-format checking
    cookie_file = "youtube_cookies.txt"
    if not os.path.exists(cookie_file) and os.path.exists("youtube_cookies.txt.txt"):
        cookie_file = "youtube_cookies.txt.txt"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extract_flat': True, # DO NOT check formats
        'force_generic_extractor': False,
    }
    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"RAILWAY: Method 2 (Flat) for {v_id}")
            info = ydl.extract_info(clean_url, download=False)
            if info:
                return {
                    "id": v_id,
                    "title": info.get("title"),
                    "thumbnail": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg",
                    "duration": info.get("duration", 0),
                    "duration_str": str(timedelta(seconds=info.get("duration", 0))),
                    "avail_heights": [360, 480, 720, 1080]
                }
        except Exception as e:
            print(f"Flat Fetch Failed: {e}")
            return {"error": "YouTube is blocking the connection. Try a different video."}

def process_video(url, mode='trim', start_time=None, end_time=None, quality_height=720):
    """TURBO ENGINE WITH COOKIE PROTECTION"""
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
            return final_output if os.path.exists(final_output) else {"error": "Save failed."}

    except Exception as e:
        print(f"PROCESS ERROR: {e}")
        return {"error": "YouTube blocked the download stream."}
