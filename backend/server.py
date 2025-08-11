##MINI BACKEND
# backend/server.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, requests, urllib.parse, re
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="YouTube Live API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # ponla en .env
DEFAULT_VIDEO_ID = os.getenv("VIDEO_ID", "f2AMDc1EOt8")  # opcional

def extract_video_id(q: str | None) -> str:
    """Acepta ID directo o URL de YouTube y devuelve el videoId."""
    if not q:
        return DEFAULT_VIDEO_ID
    if len(q) >= 10 and "/" not in q and "?" not in q:
        return q  # parece un ID
    try:
        u = urllib.parse.urlparse(q)
        if u.netloc.endswith("youtube.com"):
            qs = urllib.parse.parse_qs(u.query)
            if "v" in qs:
                return qs["v"][0]
        if u.netloc.endswith("youtu.be"):
            return u.path.lstrip("/")
    except Exception:
        pass
    return q  # último intento

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/live-data")
def get_live_video_data(video: str | None = None):
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=400, detail="Falta YOUTUBE_API_KEY")

    video_id = extract_video_id(video)
    info_url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,liveStreamingDetails,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    )
    r = requests.get(info_url, timeout=15)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"No se pudo obtener datos: {r.text}")

    data = r.json()
    if not data.get("items"):
        raise HTTPException(status_code=404, detail="Video no encontrado")

    item = data["items"][0]
    statistics = item.get("statistics", {}) or {}
    live_details = item.get("liveStreamingDetails", {}) or {}

    # concurrentViewers (si está en vivo)
    statistics["concurrentViewers"] = live_details.get("concurrentViewers", "0")

    # Live chat
    comentarios = []
    live_chat_id = live_details.get("activeLiveChatId")
    if live_chat_id:
        chat_url = (
            "https://www.googleapis.com/youtube/v3/liveChat/messages"
            f"?liveChatId={live_chat_id}&part=snippet,authorDetails&maxResults=200&key={YOUTUBE_API_KEY}"
        )
        cr = requests.get(chat_url, timeout=15)
        if cr.status_code == 200:
            for it in cr.json().get("items", []):
                autor = it["authorDetails"]["displayName"]
                mensaje = it["snippet"]["displayMessage"]
                comentarios.append({"autor": autor, "mensaje": mensaje})

    return {
        "videoId": video_id,
        "statistics": statistics,
        "liveCommentCount": len(comentarios),
        "comentarios": comentarios,
    }
