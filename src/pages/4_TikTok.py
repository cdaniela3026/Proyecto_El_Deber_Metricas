# src/pages/7_TikTok.py — Métricas TikTok Live (solo contadores)
import os
import datetime as dt
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from utils.formatting import trend_card, inject_css
from utils.charts import brand_color

API_URL = os.getenv("API_URL", "http://127.0.0.1:8001").rstrip("/")
ACCENT = brand_color("TikTok") if callable(brand_color) else "#ff0050"

st.set_page_config(page_title="TikTok Live", layout="wide")
inject_css(ACCENT)

st.markdown("## 🎵 TikTok Live — Analytics")
st.caption(f"API local: {API_URL}")

# Health check
c1, _ = st.columns([1, 6])
try:
    h = requests.get(f"{API_URL}/health", timeout=5).json()
    c1.success("API local OK ✅")
except Exception as e:
    c1.error(f"API sin respuesta: {e}")

# Auto-refresh
auto = st.toggle("Auto-actualizar cada 3s", value=True)
if auto:
    st_autorefresh(interval=3000, key="tt_live_auto")

# Consulta
try:
    with st.spinner("Consultando métricas TikTok…"):
        r = requests.get(f"{API_URL}/tiktok-stats", timeout=10)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}

    if isinstance(data, dict) and data.get("error"):
        st.error(data["error"])
    else:
        items = data.get("items", []) if isinstance(data, dict) else []
        if not items:
            st.info("Sin datos disponibles (¿el script Node está corriendo y escribiendo el JSON?).")
        else:
            info = items[0]
            s = info.get("statistics", {}) or {}

            username = s.get("username", "")
            likes = int(s.get("likes", 0))
            comments = int(s.get("comments", 0))
            viewers = int(s.get("viewers", 0))
            diamonds = int(s.get("diamonds", 0))
            shares = int(s.get("shares", 0))
            gifts_count = int(s.get("giftsCount", 0))

            if username:
                st.caption(f"Streamer: @{username}")

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            trend_card(c1, "❤️ Likes", likes, accent=ACCENT)
            trend_card(c2, "💬 Comentarios", comments, accent=ACCENT)
            trend_card(c3, "👀 Viewers", viewers, accent=ACCENT)
            trend_card(c4, "💎 Diamonds", diamonds, accent=ACCENT)
            trend_card(c5, "🔁 Shares", shares, accent=ACCENT)
            trend_card(c6, "🎁 Gifts", gifts_count, accent=ACCENT)

            st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")

except Exception as e:
    st.error(f"No se pudo obtener datos: {e}")

st.caption("Asegúrate de ejecutar el capturador Node (tiktok_live.js) y que `TIKTOK_DATA_FILE` apunte al JSON generado.")