import yt_dlp
import os
import uuid
import subprocess
import shutil
import re
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
    """Military-grade anti-block metadata fetcher."""
    if "youtu.be/" in url:
        v_id = url.split("youtu.be/")[1].split("?")[0]
        url = f"https://www.youtube.com/watch?v={v_id}"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'no_playlist': True,
        'extract_flat': False,
        'skip_download': True,
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    # ULTIMATE BYPASS: Use cookies if available (Check for double extensions too)
    cookie_file = "youtube_cookies.txt"
    if not os.path.exists(cookie_file) and os.path.exists("youtube_cookies.txt.txt"):
        cookie_file = "youtube_cookies.txt.txt"

    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file
        print(f"DEBUG: Using cookies from {cookie_file}")
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {"error": "YouTube blocked the request. Try again."}
            
            if 'entries' in info: info = info['entries'][0]

            formats = info.get("formats", [])
            heights = sorted(list(set([f.get("height") for f in formats if f.get("height")])))
            
            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "duration_str": str(timedelta(seconds=info.get("duration") or 0)),
                "avail_heights": heights
            }
        except Exception as e:
            return {"error": str(e)}

def process_video(url, mode='trim', start_time=None, end_time=None, quality_height=720):
    """
    ULTRA-TURBO INSTANT ENGINE (Sub-10 Seconds)
    Uses direct stream copying to avoid re-encoding lag.
    """
    s_sec = time_to_seconds(start_time)
    e_sec = time_to_seconds(end_time)
    duration_sec = e_sec - s_sec

    # Options for fast extraction
    ydl_opts = {
        'format': f'bestvideo[height<={quality_height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'nocheckcertificate': True,
    }
    if os.path.exists("youtube_cookies.txt"):
        ydl_opts['cookiefile'] = 'youtube_cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Single fetch for everything
            info = ydl.extract_info(url, download=False)
            
            # Setup naming
            raw_title = info.get('title', 'StreamTrim_Video')
            clean_title = re.sub(r'[^\w\s-]', '', raw_title).strip().replace(' ', '_')
            final_output = os.path.abspath(os.path.join("downloads", f"{clean_title}_{uuid.uuid4().hex[:4]}.mp4"))
            
            # Start FFmpeg Command
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

            # THE SPEED SECRET: Stream Copy instead of Re-encode
            # This makes processing 1-2 seconds regardless of video length.
            if mode == 'audio':
                cmd.extend(["-vn", "-c:a", "copy"]) # Instant audio extraction
            else:
                # Use copy for speed, with faststart for web playback
                cmd.extend(["-c", "copy", "-movflags", "faststart"])

            cmd.append(final_output)
            
            # Run FFmpeg
            subprocess.run(cmd, check=True)
            
            if os.path.exists(final_output):
                return final_output
            return {"error": "Failed to generate file."}

    except Exception as e:
        return {"error": f"Turbo Fail: {str(e)}"}
