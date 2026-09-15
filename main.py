import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# Enable CORS for your GitHub Pages website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Matches the exact JSON sent from index.html
class ClipRequest(BaseModel):
    url: str
    start_time: int
    duration: int

YDL_OPTS = {
    'format': 'best',  # Grabs the best available combined stream reliably
    'outtmpl': 'input_video.%(ext)s',
    'overwrites': True,
    'nocheckcertificate': True,
    'quiet': True,
    'no_warnings': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        }
    }
}

# Add cookies file if present on server
if os.path.exists('cookies.txt'):
    YDL_OPTS['cookiefile'] = 'cookies.txt'

@app.get("/")
def read_root():
    return {"status": "Apex Motion Clipper API is active"}

@app.post("/create-clip")
def create_clip(request: ClipRequest):
    output_file = "clipped_video.mp4"

    # Clean up old clipped files
    if os.path.exists(output_file):
        os.remove(output_file)

    # 1. Download video
    downloaded_file = None
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(request.url, download=True)
            downloaded_file = ydl.prepare_filename(info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube Download Failed: {str(e)}")

    # 2. Trim, crop to 9:16 vertical Short, and convert to MP4 using FFmpeg
    try:
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-t", str(request.duration),
            "-i", downloaded_file,
            "-vf", "crop=ih*(9/16):ih",  # Crops center into 9:16 vertical format
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg Clipping Failed: {str(e)}")
    finally:
        # Clean up downloaded raw file
        if downloaded_file and os.path.exists(downloaded_file):
            os.remove(downloaded_file)

    # 3. Return finished MP4 clip
    if os.path.exists(output_file):
        return FileResponse(output_file, media_type="video/mp4", filename="apex_short.mp4")
    
    raise HTTPException(status_code=500, detail="Clip completed but output file is missing.")
