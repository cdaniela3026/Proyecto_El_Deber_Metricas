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
import json

# =====================
# CONFIGURACIÓN GENERAL
# =====================
st.set_page_config(page_title="📊 Comparativa de Tráfico en Vivo", layout="wide")

# --- Funciones auxiliares ---
def load_tiktok_json(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"No pude leer TikTok JSON: {e}")
        return {}

def get_tiktok_viewers(data):
    try:
        return int(data["items"][0]["statistics"]["viewers"])
    except Exception:
        return 0

# --- URL RAW por defecto ---
RAW_TT_URL = "https://raw.githubusercontent.com/cdaniela3026/Proyecto_El_Deber_Metricas/main/live_data1.json"

# =====================
# ENTRADAS GENERALES
# =====================
st.title("📊 Comparativa de Tráfico en Vivo")

# Entrada para YouTube
youtube_url = st.text_input(
    "URL o ID de YouTube LIVE para el comparativo",
    value="https://www.youtube.com/watch?v=OjkHGQqcz-M"
)

# Entradas para TikTok (arriba)
st.session_state.setdefault("tt_user_input", "")
st.session_state.setdefault("tt_raw_input", RAW_TT_URL)

c_tt1, c_tt2 = st.columns([1,3])
st.session_state["tt_user_input"] = c_tt1.text_input(
    "Usuario de TikTok", 
    value=st.session_state["tt_user_input"], 
    placeholder="@tucuenta"
)
st.session_state["tt_raw_input"] = c_tt2.text_input(
    "O pega la URL JSON pública (RAW) de TikTok",
    value=st.session_state["tt_raw_input"],
    placeholder="https://raw.githubusercontent.com/usuario/repo/main/archivo.json"
)

# =====================
# KPI EN VIVO
# =====================
col1, col2 = st.columns(2)

# Simulación de viewers YouTube (en tu caso lo reemplazas por tu función real)
yt_viewers = 7107
col1.metric("YouTube (concurrentes)", yt_viewers)

# Viewers TikTok usando la URL RAW
tt_url_effective = (st.session_state["tt_raw_input"] or RAW_TT_URL).strip()
tt_json = load_tiktok_json(tt_url_effective)
tt_viewers = get_tiktok_viewers(tt_json)
col2.metric("TikTok (concurrentes)", tt_viewers)

# =====================
# GRÁFICO COMPARATIVO
# =====================
import pandas as pd
import plotly.express as px

df_live = pd.DataFrame({
    "platform": ["YouTube", "TikTok"],
    "viewers": [yt_viewers, tt_viewers]
})

fig = px.bar(df_live, x="platform", y="viewers", text="viewers", height=400)
st.plotly_chart(fig, use_container_width=True)

# =====================
# PESTAÑAS DETALLADAS
# =====================
tab_yt, tab_tt = st.tabs(["YouTube", "TikTok"])

with tab_tt:
    st.subheader("TikTok en vivo")

    c1, c2 = st.columns([1,3])
    st.session_state["tt_user_input"] = c1.text_input(
        "Usuario de TikTok",
        value=st.session_state.get("tt_user_input", ""),
        placeholder="@tucuenta",
        key="tt_user_input_tab"
    )
    st.session_state["tt_raw_input"] = c2.text_input(
        "URL JSON pública (RAW)",
        value=st.session_state.get("tt_raw_input", RAW_TT_URL),
        placeholder="https://raw.githubusercontent.com/usuario/repo/main/archivo.json",
        key="tt_raw_input_tab"
    )

    tt_url_effective = (st.session_state["tt_raw_input"] or RAW_TT_URL).strip()

    try:
        tt_json = load_tiktok_json(tt_url_effective)
        tt_viewers = get_tiktok_viewers(tt_json)
        st.metric("👀 Viewers", tt_viewers)
        with st.expander("🔎 Debug del JSON"):
            st.json(tt_json)
        st.caption(f"Fuente: {tt_url_effective}")
        if st.session_state["tt_user_input"]:
            st.caption(f"Usuario: {st.session_state['tt_user_input']}")
    except Exception as e:
        st.error(f"No pude leer el JSON de TikTok: {e}")
        st.caption(f"Intenté leer: {tt_url_effective}")

