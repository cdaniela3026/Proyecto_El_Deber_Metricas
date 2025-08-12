# local_api/main.py — YouTube + TikTok
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os, re, time, requests, json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

app = FastAPI(title="Local API - Live Analytics")

# CORS abierto (se debe ajustar si se quiere  restringir orígenes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Config común
# =========================
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "12"))

# =========================
# Helper YouTube
# =========================
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

def extract_video_id(url_or_id: str) -> Optional[str]:
    if not url_or_id:
        return None
    s = url_or_id.strip()
    if len(s) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", s):
        return s
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    return None

def yt_get_video_details(video_id: str, api_key: str) -> Dict[str, Any]:
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet,liveStreamingDetails,statistics", "id": video_id, "key": api_key}
    r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    try:
        data = r.json()
    except Exception:
        data = {"error": f"Respuesta no-JSON ({r.status_code})"}
    data["_status_code"] = r.status_code
    return data

def yt_get_live_chat_messages(live_chat_id: str, api_key: str, page_token: Optional[str] = None) -> Dict[str, Any]:
    url = "https://www.googleapis.com/youtube/v3/liveChat/messages"
    params = {"liveChatId": live_chat_id, "part": "snippet,authorDetails", "maxResults": 200, "key": api_key}
    if page_token:
        params["pageToken"] = page_token
    r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    try:
        data = r.json()
    except Exception:
        data = {"error": f"Respuesta no-JSON ({r.status_code})"}
    data["_status_code"] = r.status_code
    return data

def to_int(s: Any, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default

# =========================
# Endpoints
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

# ---- YouTube ----
@app.get("/live-data")
def live_data(video: str = Query(default="")):
    if not YOUTUBE_API_KEY:
        return {"error": "Falta YOUTUBE_API_KEY en .env"}

    vid = extract_video_id(video)
    if not vid:
        return {"items": [], "warning": "Pega una URL o ID válido de YouTube."}

    v_data = yt_get_video_details(vid, YOUTUBE_API_KEY)
    if v_data.get("_status_code") != 200:
        return {"items": [], "error": f"No se pudo obtener datos del video ({v_data.get('_status_code')})"}

    items = v_data.get("items", [])
    if not items:
        return {"items": [], "warning": "El Data API no devolvió información para este video (¿privado/restringido/solo miembros?)."}

    item0 = items[0]
    stats_raw = item0.get("statistics", {}) or {}
    live = item0.get("liveStreamingDetails", {}) or {}

    statistics: Dict[str, Any] = {
        "viewCount": to_int(stats_raw.get("viewCount", 0)),
        "likeCount": to_int(stats_raw.get("likeCount", 0)),
        "concurrentViewers": to_int(live.get("concurrentViewers", 0)),
        "actualStartTime": live.get("actualStartTime"),
        "actualEndTime": live.get("actualEndTime"),
    }

    comentarios: List[Dict[str, str]] = []
    live_chat_id = live.get("activeLiveChatId")

    if live_chat_id:
        c_data = yt_get_live_chat_messages(live_chat_id, YOUTUBE_API_KEY)
        if c_data.get("_status_code") == 200:
            for it in c_data.get("items", []):
                sn = it.get("snippet", {}) or {}
                au = it.get("authorDetails", {}) or {}
                comentarios.append({
                    "autor": au.get("displayName", ""),
                    "mensaje": sn.get("displayMessage", ""),
                    "ts": sn.get("publishedAt", ""),
                })
            statistics["liveCommentCount"] = len(comentarios)
        else:
            statistics["liveCommentCount"] = 0
    else:
        try:
            import pytchat  # type: ignore
            chat = pytchat.create(video_id=vid)
            t_end = time.time() + 2.5
            while time.time() < t_end and chat.is_alive():
                for c in chat.get().sync_items():
                    comentarios.append({
                        "autor": getattr(c.author, "name", ""),
                        "mensaje": getattr(c, "message", ""),
                        "ts": getattr(c, "timestamp", ""),
                    })
                    if len(comentarios) >= 120:
                        break
                time.sleep(0.2)
            statistics["liveCommentCount"] = len(comentarios)
        except Exception:
            statistics["liveCommentCount"] = 0

    return {"items": [{"statistics": statistics, "comentarios": comentarios}]}

# ---- TikTok ----
TIKTOK_DATA_FILE = os.getenv("TIKTOK_DATA_FILE", "live_data1.json")

@app.get("/tiktok-stats")
def tiktok_stats(
    user: str = Query(default=""),
    fallback: bool = Query(default=True)  # << se puede desactivar el fallback desde el front
):
    candidates = []
    if user:
        # buscamos live_<user>.json
        primary = Path(f"live_{user}.json")
        if primary.exists():
            p = primary
        elif fallback:
            # usamos archivo por defecto si se permite fallback
            p = Path(TIKTOK_DATA_FILE)
            if not p.exists():
                return {"items": [], "error": f"No hay datos para @{user} (y tampoco {TIKTOK_DATA_FILE})."}
        else:
            return {"items": [], "error": f"No hay datos para @{user}. Ejecuta el capturador Node para ese usuario."}
    else:
        p = Path(TIKTOK_DATA_FILE)
        if not p.exists():
            return {"items": [], "error": f"No se encontró {TIKTOK_DATA_FILE}. Ejecuta el capturador."}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"items": [], "error": f"No se pudo leer JSON: {e}"}

    gifts = data.get("gifts", []) or []
    stats = {
        "username": data.get("username", user),
        "likes": int(data.get("likes", 0)),
        "comments": int(data.get("comments", 0)),
        "viewers": int(data.get("viewers", 0)),
        "diamonds": int(data.get("diamonds", 0)),
        "shares": int(data.get("shares", 0)),
        "giftsCount": len(gifts),
    }
    return {"items": [{"platform": "TikTok", "statistics": stats, "gifts": gifts}]}

# (Opcional) ejecutar directo: python local_api/main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("local_api.main:app", host="0.0.0.0", port=8001, reload=True)