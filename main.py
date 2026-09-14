import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# Enable CORS so your GitHub Pages website can talk to Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input format sent from your website
class ClipRequest(BaseModel):
    video_url: str
    start_time: str  # Example: "00:00:10" or "10"
    end_time: str    # Example: "00:00:20" or "20"

# Fix for YouTube blocking Render IP and missing JavaScript runtime
YDL_OPTS = {
    'format': 'mp4/best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': 'input_video.mp4',
    'overwrites': True,
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

    # Clean up any leftover files from previous runs
    for f in [input_file, output_file]:
        if os.path.exists(f):
            os.remove(f)

    # 1. Download video using yt-dlp
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            ydl.download([request.video_url])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube Download Failed: {str(e)}")

    # 2. Trim video using FFmpeg
    try:
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-to", str(request.end_time),
            "-i", input_file,
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg Clipping Failed: {str(e)}")

    # 3. Return the clipped video file back to the website
    if os.path.exists(output_file):
        return FileResponse(output_file, media_type="video/mp4", filename="clip.mp4")
    
    raise HTTPException(status_code=500, detail="Clip processing completed but output file missing.")
