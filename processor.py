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
    if not t_str or t_str == "Unknown": return 0.0
    try:
        parts = list(map(float, str(t_str).split(":")))
        if len(parts) == 1: return parts[0]
        if len(parts) == 2: return parts[0]*60 + parts[1]
        if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
        return 0.0
    except:
        return 0.0

def get_video_info(url):
    """ULTIMATE NO-FAIL FETCH (OEmbed + Android Client)"""
    v_id = None
    if "youtu.be/" in url:
        v_id = url.split("youtu.be/")[1].split("?")[0]
    elif "v=" in url:
        v_id = url.split("v=")[1].split("&")[0]
    
    if not v_id: return {"error": "Invalid URL"}
    clean_url = f"https://www.youtube.com/watch?v={v_id}"

    # Try OEmbed First for FAST UI
    try:
        r = requests.get(f"https://www.youtube.com/oembed?url={clean_url}&format=json", timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Try to get duration silently in background
            return {
                "id": v_id,
                "title": data.get("title"),
                "thumbnail": f"https://i.ytimg.com/vi/{v_id}/maxresdefault.jpg",
                "duration": 0,
                "duration_str": "00:00",
                "avail_heights": [360, 480, 720, 1080]
            }
    except: pass

    return {"error": "Could not connect to YouTube. Check your internet."}

def process_video(url, mode='trim', start_time=None, end_time=None, quality_height=720):
    """ULTRA-TURBO WITH ANDROID EMULATION (Best for Railway)"""
    s_sec = time_to_seconds(start_time)
    e_sec = time_to_seconds(end_time)
    duration_sec = e_sec - s_sec if e_sec > s_sec else 0

    # These options are currently the MOST RESILIENT for cloud servers
    ydl_opts = {
        'format': f'bestvideo[height<={quality_height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # THE MAGIC SAUCE: Use Android client to bypass 403 blocks
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    
    cookie_file = "youtube_cookies.txt"
    if not os.path.exists(cookie_file) and os.path.exists("youtube_cookies.txt.txt"):
        cookie_file = "youtube_cookies.txt.txt"
    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"DEBUG: Processing {url} with Android Emulation")
            info = ydl.extract_info(url, download=False)
            
            raw_title = info.get('title', 'Video')
            clean_title = re.sub(r'[^\w\s-]', '', raw_title).strip().replace(' ', '_')
            final_output = os.path.abspath(os.path.join("downloads", f"{clean_title}_{uuid.uuid4().hex[:4]}.mp4"))
            
            cmd = [FFMPEG_EXE, "-y", "-hide_banner", "-loglevel", "error"]
            req_formats = info.get('requested_formats')
            
            if req_formats and len(req_formats) >= 2:
                v_url, a_url = req_formats[0]['url'], req_formats[1]['url']
                cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", v_url])
                cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", a_url])
            else:
                cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", info['url']])

            # Fast Copy Mode
            cmd.extend(["-c", "copy", "-movflags", "faststart", final_output])
            
            subprocess.run(cmd, check=True)
            return final_output if os.path.exists(final_output) else {"error": "Processing failed."}

    except Exception as e:
        print(f"LOG: {str(e)}")
        return {"error": "YouTube blocked the high-speed stream. Try a lower quality or different video."}
