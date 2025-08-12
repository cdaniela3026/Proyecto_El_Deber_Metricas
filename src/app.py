## PROYECTO ANALISIS DE METRICAS REDES SOCIALES EL DEBER
## VERSION 1
## FECHA: 09/08/2025
## RESPONSABLE FRONT: CARLA DANIELA SORUCO MAERTENS
#=====================================================================================
# src/app.py — YouTube + TikTok
# -> 3 gráficas por pestaña: línea (tiempo real), barras (snapshot) y donut (snapshot)
# -> TikTok y Youtube limpio si no hay usuario consultado
# =====================================================================================

# app.py — Streamlit Cloud (Opción A: consulta directa a YouTube)
import os, re, datetime as dt, requests, streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.express as px

# Cargar secretos
if st.secrets:
    os.environ.update({k: str(v) for k, v in st.secrets.items()})
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
DEFAULT_VIDEO_ID = os.getenv("VIDEO_ID", "").strip()

_YT_ID_RE = re.compile(r"""
    (?:https?://)?
    (?:www\.)?
    (?:
        youtu\.be/(?P<id1>[A-Za-z0-9_-]{11})
        |
        youtube\.com/
            (?:
                (?:watch\?.*?v=|live/|embed/|shorts/)
                (?P<id2>[A-Za-z0-9_-]{11})
            )
    )
""", re.VERBOSE)

def yt_normalize_id(text: str) -> str:
    if not text: return ""
    text = text.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text): return text
    m = _YT_ID_RE.search(text)
    if m: return m.group("id1") or m.group("id2") or ""
    if "v=" in text:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(text).query)
        vid = qs.get("v", [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid): return vid
    return text

def fetch_youtube_live(video_id: str):
    if not YOUTUBE_API_KEY:
        return False, {"error": "Falta YOUTUBE_API_KEY en Secrets"}, None
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "liveStreamingDetails,statistics", "id": video_id, "key": YOUTUBE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=12)
        status = r.status_code
        try: payload = r.json()
        except Exception: payload = {"raw": r.text}
        return 200 <= status < 300, payload, status
    except Exception as e:
        return False, {"error": str(e)}, None

def _bar_and_pie_from_last(df_long, title_prefix, color_map):
    fig_bar = px.bar(df_long, x="metric", y="value", text="value",
        title=f"{title_prefix} — snapshot (barras)",
        color="metric", color_discrete_map=color_map)
    fig_bar.update_traces(textposition="outside", cliponaxis=False)
    fig_bar.update_layout(margin=dict(l=10,r=10,t=40,b=0), height=320, showlegend=False)
    fig_pie = px.pie(df_long, names="metric", values="value", hole=0.55,
        title=f"{title_prefix} — snapshot (donut)",
        color="metric", color_discrete_map=color_map)
    fig_pie.update_traces(textposition="inside", texttemplate='%{percent:.1%}')
    fig_pie.update_layout(margin=dict(l=10,r=10,t=40,b=0), height=320, legend_title_text="")
    return fig_bar, fig_pie

st.set_page_config(page_title="EL DEBER — ANÁLISIS DE TRANSMISIÓN EN VIVO", layout="wide")
st.markdown("<h2 style='margin:0'>EL DEBER — ANÁLISIS DE TRANSMISIÓN EN VIVO</h2>", unsafe_allow_html=True)
st.divider()

# ----- Resumen superior
st.subheader("📡 Resumen comparativo en vivo")
col1, col2, _ = st.columns([1,1,6])
auto_top = col1.toggle("Auto-actualizar 20s", value=True, key="top_auto")
if auto_top: st_autorefresh(interval=20000, key="top_auto_key")

st.session_state.setdefault("yt_hist", [])
st.session_state.setdefault("yt_q", DEFAULT_VIDEO_ID)
yt_video_q = st.text_input("ID/URL del LIVE de YouTube para el comparativo (arriba)",
                           value=st.session_state.get("yt_q",""),
                           placeholder="https://www.youtube.com/watch?v=VIDEO_ID o VIDEO_ID",
                           key="yt_comp_input")
st.session_state["yt_q"] = yt_video_q
video_id_top = yt_normalize_id(yt_video_q)

yt_value, yt_note = 0, ""
if video_id_top:
    ok, data, status = fetch_youtube_live(video_id_top)
    if ok:
        items = data.get("items", [])
        if items:
            node = items[0]; live = node.get("liveStreamingDetails", {}) or {}; stats = node.get("statistics", {}) or {}
            yt_value = int(live.get("concurrentViewers") or stats.get("concurrentViewers") or 0)
        else: yt_note = "Sin items (¿no está LIVE?)"
    else: yt_note = f"YT status {status}: {data}"

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("YouTube (concurrentes)", f"{yt_value}")
k2.metric("TikTok", "—"); k3.metric("Instagram", "—"); k4.metric("Facebook", "—"); k5.metric("X", "—")

df_top = pd.DataFrame([{"platform":"YouTube","views":yt_value}])
fig_top = px.bar(df_top, x="platform", y="views", text="views", title="Tráfico en vivo por plataforma (YouTube directo)")
fig_top.update_traces(textposition="outside", cliponaxis=False)
fig_top.update_layout(margin=dict(l=10,r=10,t=40,b=20), height=280, showlegend=False, yaxis_title="viewers")
st.plotly_chart(fig_top, use_container_width=True)
if yt_note: st.caption(yt_note)
st.divider()

tab_yt, tab_tt = st.tabs(["YouTube", "TikTok"])

with tab_yt:
    st.subheader("YouTube en vivo (directo a API)")
    if "yt_run" not in st.session_state: st.session_state["yt_run"] = False
    q = st.text_input("Pega la URL o ID de un video en vivo (acepta youtu.be).",
                      value=DEFAULT_VIDEO_ID,
                      placeholder="https://www.youtube.com/watch?v=VIDEO_ID o VIDEO_ID",
                      key="yt_input_v2")
    colA, colB, colDbg, _ = st.columns([1,1,1,5])
    run_click = colA.button("Consultar", type="primary", key="yt_btn_v2")
    yt_auto   = colB.toggle("Auto-actualizar 20s", value=True, key="yt_auto_v2")
    yt_debug  = colDbg.toggle("Debug", value=False, key="yt_dbg_v2")
    if run_click and q:
        st.session_state["yt_q"] = q
        st.session_state["yt_run"] = True
        st.session_state["yt_hist"] = []
    video_id = yt_normalize_id(st.session_state.get("yt_q", q))
    if yt_auto and st.session_state.get("yt_run") and video_id:
        st_autorefresh(interval=20000, key="yt_live_auto_v2")
    st.subheader("📊 Métricas en vivo")
    yt_snap, dbg_raw = None, None
    if st.session_state.get("yt_run") and video_id:
        ok, data, status = fetch_youtube_live(video_id)
        dbg_raw = {"ok": ok, "status": status, "payload": data}
        if not ok: st.error(f"Error YouTube API (status {status}).")
        items = data.get("items", []) if isinstance(data, dict) else []
        if not items:
            st.warning("No se recibieron datos del live (¿está LIVE? ¿cuota?).")
        else:
            node = items[0] or {}; stats = (node.get("statistics") or {}); live  = (node.get("liveStreamingDetails") or {})
            view_count = int(stats.get("viewCount") or node.get("viewCount") or 0)
            like_count = int(stats.get("likeCount") or node.get("likeCount") or 0)
            concurrent = int(live.get("concurrentViewers") or stats.get("concurrentViewers") or 0)
            live_comments = int(node.get("liveCommentCount") or stats.get("liveCommentCount") or 0)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👀 Vistas", f"{view_count}"); c2.metric("👍 Me gusta", f"{like_count}")
            c3.metric("🟢 Concurrentes", f"{concurrent}"); c4.metric("💬 Comentarios (live)", f"{live_comments}")
            st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")
            yt_snap = {"ts": pd.Timestamp.utcnow(), "views": concurrent or view_count, "likes": like_count, "comments": live_comments}
    if yt_debug and dbg_raw is not None:
        with st.expander("🔎 Debug de respuesta de la API"): st.json(dbg_raw)
    if yt_snap is not None:
        st.session_state["yt_hist"] = (st.session_state["yt_hist"] + [yt_snap])[-200:]
    if st.session_state["yt_hist"]:
        df_y = pd.DataFrame(st.session_state["yt_hist"])
        fig_y = px.line(df_y, x="ts", y=["views","likes","comments"], title="Evolución en vivo — YouTube", markers=True)
        fig_y.update_layout(margin=dict(l=10,r=10,t=40,b=0), height=320, legend_title_text="")
        st.plotly_chart(fig_y, use_container_width=True)
        row = df_y.iloc[-1]
        df_y_last = pd.DataFrame({"metric":["views","likes","comments"],
                                  "value":[int(row.get("views",0)), int(row.get("likes",0)), int(row.get("comments",0))]})
        cb1, cb2 = st.columns(2)
        fig_bar, fig_pie = _bar_and_pie_from_last(df_y_last, "YouTube", {"views":"#16a34a","likes":"#FF0000","comments":"#fbbf24"})
        cb1.plotly_chart(fig_bar, use_container_width=True); cb2.plotly_chart(fig_pie, use_container_width=True)

with tab_tt:
    st.subheader("TikTok en vivo")
    st.info("En Streamlit Cloud esta pestaña requiere backend propio o archivo JSON público. Por ahora se muestra solo YouTube directo.")
