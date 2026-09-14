from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import subprocess

app = FastAPI(title="Apex Motion Clipper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClipRequest(BaseModel):
    url: str
    start_time: int  # in seconds
    duration: int    # in seconds (e.g., 30 for a 30s short)

@app.get("/")
def home():
    return {"status": "Apex Motion Clipper API is active"}

@app.post("/create-clip")
def create_clip(request: ClipRequest):
    os.makedirs("/tmp/clips", exist_ok=True)
    output_filename = f"/tmp/clips/short_{request.start_time}_{request.duration}.mp4"
    
    # Extract direct video/audio stream URL without downloading full video
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            stream_url = info.get('url')
            
            if not stream_url:
                # If separate streams exist, fetch primary video stream
                formats = info.get('formats', [])
                for fmt in formats:
                    if fmt.get('vcodec') != 'none':
                        stream_url = fmt.get('url')
                        break

        if not stream_url:
            raise HTTPException(status_code=400, detail="Could not retrieve playable video stream.")

        # FFmpeg command: Cut clip and crop from 16:9 (horizontal) to 9:16 (vertical Short)
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(request.start_time),
            "-i", stream_url,
            "-t", str(request.duration),
            "-vf", "crop=ih*(9/16):ih",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-strict", "experimental",
            output_filename
        ]

        subprocess.run(ffmpeg_cmd, check=True)
        return FileResponse(output_filename, media_type="video/mp4", filename="short_clip.mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
