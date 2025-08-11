import os
import requests
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import timedelta
from streamlit_autorefresh import st_autorefresh

from utils.charts import branded_line, brand_color
from utils.formatting import trend_card, inject_css

# ---------- Config ----------
st.set_page_config(page_title="▶️ YouTube", layout="wide")
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "sample"
PLATFORM = "YouTube"
ACCENT = brand_color(PLATFORM)
inject_css(ACCENT)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8001").rstrip("/")

st.header("▶️ YouTube Live — Análisis")

# Tabs: histórico (muestra) y Live (API)
tab_hist, tab_live = st.tabs(["Histórico (muestra)", "Live (API)"])

# ===================== TAB 1 — HISTÓRICO (MUESTRA) =====================
with tab_hist:
    st.caption("Datos de muestra — luego conectamos API oficial.")

    # Carga de CSV de ejemplo (si existe)
    df = pd.DataFrame()
    sample_file = DATA_DIR / "sample_posts.csv"
    if sample_file.exists():
        df = pd.read_csv(sample_file, parse_dates=["date"])
        df = df[df["platform"] == PLATFORM]

    if df.empty:
        st.info("Sin datos de YouTube (muestra).")
    else:
        min_d, max_d = df["date"].min().date(), df["date"].max().date()
        default_from = max(min_d, max_d - timedelta(days=30))

        st.sidebar.subheader("Filtros YouTube")
        f = st.sidebar.date_input("Desde", default_from, min_value=min_d, max_value=max_d, key="yt_from")
        t = st.sidebar.date_input("Hasta", max_d, min_value=min_d, max_value=max_d, key="yt_to")

        df_now = df[(df["date"].dt.date >= f) & (df["date"].dt.date <= t)]

        c1, c2, c3 = st.columns(3)
        trend_card(c1, "Publicaciones", int(df_now["posts"].sum()), accent=ACCENT)
        trend_card(c2, "Vistas", int(df_now["views"].sum()), accent=ACCENT)
        trend_card(c3, "Interacciones", int(df_now["interactions"].sum()), accent=ACCENT)

        st.markdown("### Vistas por día")
        ts = df_now.groupby("date", as_index=False)["views"].sum()
        fig = branded_line(ts, "date", "views", "Vistas por día", single_platform=PLATFORM)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Detalle")
        st.dataframe(df_now.sort_values("date", ascending=False), use_container_width=True)

# ===================== TAB 2 — LIVE (API) =====================
with tab_live:
    st.caption(f"API local: {API_URL}")

    # --- Health check ---
    hc1, _ = st.columns([1, 6])
    try:
        h = requests.get(f"{API_URL}/health", timeout=5).json()
        if h.get("status") == "ok":
            hc1.success("API local OK ✅")
        else:
            hc1.warning("API respondió, pero no OK")
    except Exception as e:
        hc1.error(f"API sin respuesta: {e}")

    # --- Entrada: URL/ID del video, botón y auto-refresh ---
    q = st.text_input(
        "Pega la URL o ID de un video en vivo (también acepta youtu.be).",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID o https://youtu.be/VIDEO_ID",
        key="yt_live_input",
    )

    colA, colB, _ = st.columns([1, 1, 6])
    btn = colA.button("Consultar", type="primary")
    auto = colB.toggle("Auto-actualizar cada 3s", value=True)

    # Estado para recordar el último video consultado
    if "yt_q" not in st.session_state:
        st.session_state["yt_q"] = ""

    if btn and q:
        st.session_state["yt_q"] = q
        st.toast("Consultando…", icon="⏳")

    query = st.session_state.get("yt_q", "")

    if auto and query:
        st_autorefresh(interval=3000, key="yt_live_auto")

    # --- Consulta de métricas (solo contadores) ---
    if query:
        try:
            with st.spinner("Obteniendo métricas del live…"):
                resp = requests.get(f"{API_URL}/live-data", params={"video": query}, timeout=15)
                data = resp.json()

            if isinstance(data, dict) and data.get("error"):
                st.error(data["error"])
                st.stop()
            if isinstance(data, dict) and data.get("warning"):
                st.warning(data["warning"])

            items = data.get("items", []) if isinstance(data, dict) else []
            if not items:
                st.info("No se recibieron datos del live (¿está realmente en vivo?).")
            else:
                stats = (items[0].get("statistics", {}) if items else {}) or {}

                vistas  = int(stats.get("viewCount", 0))
                likes   = int(stats.get("likeCount", 0))
                conc    = int(stats.get("concurrentViewers", 0))
                coment  = int(stats.get("liveCommentCount", 0))

                c1, c2, c3, c4 = st.columns(4)
                trend_card(c1, "👀 Vistas", vistas, accent=ACCENT)
                trend_card(c2, "👍 Le gusta", likes, accent=ACCENT)
                trend_card(c3, "🟢 Concurrentes", conc, accent=ACCENT)
                trend_card(c4, "💬 Comentarios (live)", coment, accent=ACCENT)

                st.caption("Última actualización: ")
        except Exception as e:
            st.error(f"No se pudo obtener datos: {e}")

    st.caption("Si activas el auto-refresh, se volverá a consultar cada 3 segundos mientras haya un video seleccionado.")
