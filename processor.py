import yt_dlp
import os
import uuid
import subprocess
import shutil
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
    # Handle youtu.be links
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
    
    # ULTIMATE BYPASS: Use cookies if available
    if os.path.exists("youtube_cookies.txt"):
        ydl_opts['cookiefile'] = 'youtube_cookies.txt'
        print("DEBUG: Using cookies for YouTube fetch")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"RAILWAY FETCH START: {url}")
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return {"error": "YouTube blocked the request. Try again in 5 seconds."}
            
            print(f"RAILWAY FETCH SUCCESS: {info.get('title')}")
            
            # Handle entries (if playlist link used)
            if 'entries' in info:
                info = info['entries'][0]

            formats = info.get("formats", [])
            heights = sorted(list(set([f.get("height") for f in formats if f.get("height")])))
            if not heights: heights = [360, 480, 720, 1080]
            
            # Default heights if none found
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
            return {"error": f"YouTube Access Error: {str(e)}"}

def process_video(url, mode='trim', start_time=None, end_time=None, quality_height=720):
    """
    UNIVERSAL COMPATIBLE DOWNLOADER
    Uses Video Title for the filename.
    """
    import re
    
    # 1. Get Title for naming
    ydl_opts_info = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        raw_title = info_dict.get('title', 'StreamTrim_Video')
        
    # Sanitize title (remove non-alphanumeric chars)
    clean_title = re.sub(r'[^\w\s-]', '', raw_title).strip().replace(' ', '_')
    unique_id = uuid.uuid4().hex[:6]
    final_output = os.path.abspath(os.path.join("downloads", f"{clean_title}_{unique_id}.mp4"))
    
    s_sec = time_to_seconds(start_time)
    e_sec = time_to_seconds(end_time)
    duration_sec = e_sec - s_sec

    # Format Logic for direct URL extraction
    if mode == 'audio':
        format_str = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        # Prefer MP4/M4A for native FFmpeg streaming
        format_str = f"bestvideo[height<={quality_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality_height}][ext=mp4]/best"

    ydl_opts = {
        'format': format_str,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Step 1: Extract direct stream URLs (takes < 2 seconds)
            info = ydl.extract_info(url, download=False)
            
            # Step 2: Build FFmpeg command with input seeking
            # This is the secret to speed: FFmpeg fetches ONLY the bytes it needs
            cmd = [FFMPEG_EXE, "-y", "-hide_banner", "-loglevel", "error"]
            
            req_formats = info.get('requested_formats')
            
            if req_formats and len(req_formats) >= 2:
                # Video and Audio are separate (DASH)
                v_url = req_formats[0]['url']
                a_url = req_formats[1]['url']
                
                if mode == 'trim':
                    # Seek on both inputs BEFORE -i for instant jump
                    cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", v_url])
                    cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", a_url])
                else:
                    cmd.extend(["-i", v_url, "-i", a_url])
            else:
                # Single merged stream or audio only
                stream_url = info['url']
                if mode == 'trim':
                    cmd.extend(["-ss", str(s_sec), "-t", str(duration_sec), "-i", stream_url])
                else:
                    cmd.extend(["-i", stream_url])

            # Step 3: Fast Encoding (H.264 + AAC for universal support)
            if mode == 'audio':
                cmd.extend(["-vn", "-acodec", "aac", "-b:a", "192k"])
            else:
                cmd.extend([
                    "-vcodec", "libx264", "-preset", "ultrafast", 
                    "-acodec", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
                    "-movflags", "faststart"
                ])

            cmd.append(final_output)

            # Step 4: Execute (FFmpeg now streams data from YouTube directly)
            subprocess.run(cmd, check=True)

            if os.path.exists(final_output):
                return final_output
            return {"error": "Processing failed to generate file."}

    except Exception as e:
        return {"error": f"Processing crash: {str(e)}"}
