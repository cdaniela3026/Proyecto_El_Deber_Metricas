## PROYECTO ANALISIS DE METRICAS REDES SOCIALES EL DEBER
## VERSION 1
## FECHA: 09/08/2025
## RESPONSABLE FRONT: CARLA DANIELA SORUCO MAERTENS
#=====================================================================================
# src/app.py — YouTube + TikTok
# -> 3 gráficas por pestaña: línea (tiempo real), barras (snapshot) y donut (snapshot)
# -> TikTok y Youtube limpio si no hay usuario consultado
# =====================================================================================

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# =====================
# CONFIGURACIÓN
# =====================
st.set_page_config(page_title="Métricas en Vivo", layout="wide")

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
RAW_TT_URL = "https://raw.githubusercontent.com/cdaniela3026/Proyecto_El_Deber_Metricas/main/live_data1.json"

# =====================
# FUNCIONES
# =====================
@st.cache_data(ttl=10)
def load_tiktok_json(url: str):
    """Carga datos de TikTok desde un JSON público en GitHub"""
    try:
        r = requests.get(f"{url}?nocache={datetime.utcnow().timestamp()}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"No pude leer TikTok JSON: {e}")
        return {}

def get_tiktok_viewers(data: dict):
    """Obtiene el número de viewers desde el JSON de TikTok"""
    return data.get("viewers", 0)

def get_youtube_live_viewers(video_id: str):
    """Consulta viewers concurrentes de un LIVE de YouTube"""
    if not YOUTUBE_API_KEY:
        st.error("Falta la API Key de YouTube en Secrets")
        return 0
    try:
        url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=liveStreamingDetails&id={video_id}&key={YOUTUBE_API_KEY}"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return int(data["items"][0]["liveStreamingDetails"].get("concurrentViewers", 0))
    except Exception as e:
        st.error(f"No pude obtener datos de YouTube: {e}")
        return 0

# =====================
# UI
# =====================
st.title("📊 Comparativa de Tráfico en Vivo")

yt_url = st.text_input(
    "URL o ID de YouTube LIVE para el comparativo",
    "https://www.youtube.com/watch?v=OjkHGQqcz-M"
)

video_id = yt_url.split("v=")[-1] if "v=" in yt_url else yt_url

col1, col2 = st.columns(2)
with col1:
    yt_viewers = get_youtube_live_viewers(video_id)
    st.metric("YouTube (concurrentes)", yt_viewers)
with col2:
    tt_data = load_tiktok_json(RAW_TT_URL)
    tt_viewers = get_tiktok_viewers(tt_data)
    st.metric("TikTok (concurrentes)", tt_viewers)

# =====================
# GRÁFICO COMPARATIVO
# =====================
df = pd.DataFrame({
    "platform": ["YouTube", "TikTok"],
    "viewers": [yt_viewers, tt_viewers]
})

st.bar_chart(df.set_index("platform"))

