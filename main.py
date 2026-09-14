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
    'format': 'mp4/best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': 'input_video.mp4',
    'overwrites': True,
    'cookiefile': 'cookies.txt',  # Passes your exported cookies to bypass YouTube bot detection
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'mweb']
        }
    }
}

@app.get("/")
def read_root():
    return {"status": "Apex Motion Clipper API is active"}

@app.post("/create-clip")
def create_clip(request: ClipRequest):
    input_file = "input_video.mp4"
    output_file = "clipped_video.mp4"

    # Clean up leftover files from previous runs
    for f in [input_file, output_file]:
        if os.path.exists(f):
            os.remove(f)

    # 1. Download video using cookies
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            ydl.download([request.url])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube Download Failed: {str(e)}")

    # 2. Trim and crop to 9:16 vertical Short format using FFmpeg
    try:
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-t", str(request.duration),
            "-i", input_file,
            "-vf", "crop=ih*(9/16):ih", # Crops center into 9:16 vertical format
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg Clipping Failed: {str(e)}")

    # 3. Return finished clip to the frontend
    if os.path.exists(output_file):
        return FileResponse(output_file, media_type="video/mp4", filename="apex_short.mp4")
    
    raise HTTPException(status_code=500, detail="Clip completed but output file is missing.")
