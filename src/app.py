## PROYECTO ANALISIS DE METRICAS REDES SOCIALES EL DEBER
## VERSION 1
## FECHA: 09/08/2025
## RESPONSABLE FRONT: CARLA DANIELA SORUCO MAERTENS
#=====================================================================================
# src/app.py — YouTube + TikTok
# -> 3 gráficas por pestaña: línea (tiempo real), barras (snapshot) y donut (snapshot)
# -> TikTok y Youtube limpio si no hay usuario consultado
# =====================================================================================


import os
import base64
import datetime as dt
import requests
from requests.adapters import HTTPAdapter, Retry
from dotenv import load_dotenv
import streamlit as st
import re
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import pandas as pd
import datetime as dt

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
    if not text:
        return ""
    text = text.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text
    m = _YT_ID_RE.search(text)
    if m:
        return m.group("id1") or m.group("id2") or ""
    if "v=" in text:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(text).query)
        vid = qs.get("v", [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            return vid
    return text
from streamlit_autorefresh import st_autorefresh

import pandas as pd
import plotly.express as px

# =========================
# Configuración & Helpers
# =========================
load_dotenv()

LOCAL_API = os.getenv("LOCAL_API_BASE", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_VIDEO_ID = os.getenv("VIDEO_ID", "").strip()

PLATFORM_COLORS = {
    "YouTube": "#FF0000",
    "TikTok":  "#67D6E2",
    "Instagram": "#FF4F86",
    "X": "#000000",
    "Facebook": "#1877F2",
}

def http_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

SESSION = http_session()
TIMEOUT = 15

def api_get(path: str, params=None):
    url = f"{LOCAL_API}{path}"
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def api_get_debug(path: str, params=None):
    """
    Returns (ok, data_or_text, status_code). ok=True if 2xx and JSON parsed,
    otherwise False with text/JSON.
    """
    url = f"{LOCAL_API}{path}"
    try:
        r = SESSION.get(url, params=params, timeout=TIMEOUT)
        status = r.status_code
        try:
            data = r.json()
        except Exception:
            data = r.text
        ok = 200 <= status < 300
        return ok, data, status
    except Exception as e:
        return False, str(e), None


# =========================
# UI - Streamlit
# =========================
st.set_page_config(page_title="EL DEBER — ANÁLISIS DE TRANSMISIÓN EN VIVO", layout="wide")

# Encabezado con logo de EL DEBER
LOGO_PATH = os.getenv("LOGO_PATH", "assets/el_deber.webp")
_logo_html = ""
try:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = "png" if LOGO_PATH.lower().endswith(".png") else "webp"
        _logo_html = f'<img src="data:image/{ext};base64,{b64}" alt="EL DEBER" height="34">'
except Exception:
    _logo_html = ""

if not _logo_html:
    _logo_html = '<span style="font-weight:800;color:#0a6e3a;font-family:system-ui,Segoe UI,Arial">EL DEBER</span>'

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:.75rem;">
      {_logo_html}
      <span style="font-size:1.2rem;font-weight:800;letter-spacing:.3px;">ANÁLISIS DE TRANSMISIÓN EN VIVO</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# =========================
# Resumen comparativo en vivo (arriba de las tabs)
# =========================
import time

PLATFORM_COLOR_MAP = {
    "YouTube": "#FF0000",
    "TikTok":  "#67D6E2",
    "Instagram": "#FF4F86",
    "X": "#000000",
    "Facebook": "#1877F2",
}

# Cache suave en sesión para no golpear tanto la API
st.session_state.setdefault("_live_cache", {})  # {key: (ts, data)}
def _get_cached(key, ttl=30):
    it = st.session_state["_live_cache"].get(key)
    if not it: return None
    ts, data = it
    return data if (time.time() - ts) < ttl else None

def _set_cached(key, data):
    st.session_state["_live_cache"][key] = (time.time(), data)

def fetch_youtube_concurrent(video_q: str) -> dict:
    """Devuelve {'value': int, 'status': 'ok'|'warn', 'note': str}"""
    vid = yt_normalize_id(video_q or os.getenv("VIDEO_ID", "")) if 'yt_normalize_id' in globals() else (video_q or os.getenv("VIDEO_ID", ""))
    if not vid:
        return {"value": 0, "status": "warn", "note": "Sin VIDEO_ID"}
    cache = _get_cached(f"yt:{vid}", ttl=30)
    if cache: return cache
    try:
        if 'api_get_debug' in globals():
            ok, data, status = api_get_debug("/live-data", params={"video": vid})
        else:
            data = api_get("/live-data", params={"video": vid}); ok=True; status=200
        items = (data.get("items") if isinstance(data, dict) else []) if ok else []
        if not ok:
            out = {"value": 0, "status":"warn", "note": f"YT {status}"}
        elif not items:
            out = {"value": 0, "status":"warn", "note": "Sin datos (¿no está LIVE?)"}
        else:
            node = items[0] or {}
            live = node.get("liveStreamingDetails", {}) or {}
            stats = node.get("statistics", {}) or {}
            concurrent = int(live.get("concurrentViewers") or stats.get("concurrentViewers") or 0)
            out = {"value": concurrent, "status":"ok", "note": ""}
    except Exception as e:
        out = {"value": 0, "status":"warn", "note": f"YT err: {e}"}
    _set_cached(f"yt:{vid}", out)
    return out

def fetch_tiktok_viewers(user_q: str) -> dict:
    """Devuelve {'value': int, 'status': 'ok'|'warn', 'note': str}"""
    user = (user_q or st.session_state.get("tt_user") or os.getenv("TIKTOK_USER","")).strip().lstrip("@")
    if not user:
        return {"value": 0, "status":"warn", "note":"Sin usuario TikTok"}
    cache = _get_cached(f"tt:{user}", ttl=10)
    if cache: return cache
    try:
        data = api_get("/tiktok-stats", params={"user": user})
        items = data.get("items", []) if isinstance(data, dict) else []
        if not items:
            out = {"value": 0, "status":"warn", "note":"TT sin datos"}
        else:
            s = items[0].get("statistics", {}) or {}
            viewers = int(s.get("viewers", 0))
            out = {"value": viewers, "status":"ok", "note": ""}
    except Exception as e:
        out = {"value": 0, "status":"warn", "note": f"TT err: {e}"}
    _set_cached(f"tt:{user}", out)
    return out

st.subheader("📡 Resumen comparativo en vivo")
c1, c2, c3 = st.columns([1,1,6])
auto_refresh_top = c1.toggle("Auto-actualizar 20s", value=True, key="top_auto_refresh")
interval_top = 20000  # ms
if auto_refresh_top:
    try:
        st_autorefresh(interval=interval_top, key="top_live_auto")
    except Exception:
        pass

yt_video_q = st.session_state.get("yt_q", os.getenv("VIDEO_ID", "")) if 'st' in globals() else os.getenv("VIDEO_ID", "")
tt_user_q  = st.session_state.get("tt_user", os.getenv("TIKTOK_USER", "")) if 'st' in globals() else os.getenv("TIKTOK_USER", "")

yt = fetch_youtube_concurrent(yt_video_q)
tt = fetch_tiktok_viewers(tt_user_q)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("YouTube (concurrentes)", f"{yt['value']}")
k2.metric("TikTok (viewers)", f"{tt['value']}")
k3.metric("Instagram", "—")
k4.metric("Facebook", "—")
k5.metric("X", "—")

import pandas as pd, plotly.express as px
df_live = pd.DataFrame([
    {"platform":"YouTube", "views": yt["value"]},
    {"platform":"TikTok",  "views": tt["value"]},
])
fig_top = px.bar(
    df_live, x="platform", y="views", text="views",
    title="Tráfico en vivo por plataforma",
    color="platform",
    color_discrete_map=PLATFORM_COLOR_MAP,
)
fig_top.update_traces(textposition="outside", cliponaxis=False)
fig_top.update_layout(margin=dict(l=10,r=10,t=40,b=20), height=320, showlegend=False, yaxis_title="viewers")
st.plotly_chart(fig_top, use_container_width=True)

notes = []
if yt["status"] != "ok" and yt.get("note"):
    notes.append(f"YouTube: {yt['note']}")
if tt["status"] != "ok" and tt.get("note"):
    notes.append(f"TikTok: {tt['note']}")
if notes:
    st.caption(" · ".join(notes))
st.divider()
# Health
hc1, _ = st.columns([1, 5])
try:
    _ = api_get("/health")
    hc1.success("API local OK ✅")
except Exception as e:
    hc1.error(f"API local no responde: {e}")

st.divider()

# =========================
# Tabs: YouTube + TikTok
# =========================
tab_yt, tab_tt = st.tabs(["YouTube", "TikTok"])

# --------- util gráficos snapshot
def _bar_and_pie_from_last(df_long, title_prefix, color_map):
    """
    df_long: DataFrame con columnas ['metric','value'] del último snapshot.
    Devuelve (fig_bar, fig_pie)
    """
    fig_bar = px.bar(
        df_long, x="metric", y="value",
        text="value",
        title=f"{title_prefix} — snapshot actual (barras)",
        color="metric",
        color_discrete_map=color_map,
    )
    fig_bar.update_traces(textposition="outside", cliponaxis=False)
    fig_bar.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, showlegend=False)

    fig_pie = px.pie(
        df_long,
        names="metric",
        values="value",
        hole=0.55,
        title=f"{title_prefix} — snapshot actual (donut)",
        color="metric",
        color_discrete_map=color_map,
    )
    fig_pie.update_traces(textposition="inside", texttemplate='%{percent:.1%}')
    fig_pie.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")

    return fig_bar, fig_pie


# -------------------------
# TAB 2 — TikTok
# -------------------------
with tab_tt:
    st.subheader("TikTok en vivo")

    if "tt_user" not in st.session_state:
        st.session_state["tt_user"] = ""
    if "tt_run" not in st.session_state:
        st.session_state["tt_run"] = False
    st.session_state.setdefault("tt_hist", [])

    colU, colBtn, colAuto = st.columns([3, 1, 2])
    user_input = colU.text_input(
        "Usuario de TikTok (sin @)",
        value=st.session_state["tt_user"],
        placeholder="ej. jorgepadilla_01",
        key="tt_input",
    )
    run_tt = colBtn.button("Consultar", key="tt_btn")
    tt_auto = colAuto.toggle("Auto-actualizar cada 3s", value=True, key="tt_auto")

    if run_tt and user_input:
        st.session_state["tt_user"] = user_input.strip().lstrip("@")
        st.session_state["tt_run"] = True
        st.session_state["tt_hist"] = []      # reset historial

    tt_user = st.session_state.get("tt_user", "")

    if tt_auto and st.session_state.get("tt_run") and tt_user:
        st_autorefresh(interval=3000, key="tt_live_auto")

    tt_snap = None

    # TikTok limpio si no hay usuario consultado
    if st.session_state.get("tt_run") and tt_user:
        try:
            data = api_get("/tiktok-stats", params={"user": tt_user})
            if isinstance(data, dict) and data.get("error"):
                st.error(data["error"])
            else:
                items = data.get("items", []) if isinstance(data, dict) else []
                if not items:
                    st.info("Sin datos disponibles (¿el script Node está corriendo y escribiendo el JSON?).")
                else:
                    info = items[0]
                    s = info.get("statistics", {}) or {}

                    username   = s.get("username", tt_user)
                    likes      = int(s.get("likes", 0))
                    comments   = int(s.get("comments", 0))
                    viewers    = int(s.get("viewers", 0))
                    diamonds   = int(s.get("diamonds", 0))
                    shares     = int(s.get("shares", 0))
                    gifts_cnt  = int(s.get("giftsCount", 0))

                    if username:
                        st.caption(f"Streamer: @{username}")

                    d1, d2, d3, d4, d5, d6 = st.columns(6)
                    d1.metric("❤️ Me gusta", f"{likes}")
                    d2.metric("💬 Comentarios", f"{comments}")
                    d3.metric("👀 Espectadores", f"{viewers}")
                    d4.metric("💎 Diamantes", f"{diamonds}")
                    d5.metric("🔁 Acciones", f"{shares}")
                    d6.metric("🎁 Regalos", f"{gifts_cnt}")

                    st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")

                    tt_snap = {
                        "ts": pd.Timestamp.utcnow(),
                        "viewers": viewers,
                        "likes": likes,
                        "comments": comments,
                        "diamonds": diamonds,
                    }

        except requests.HTTPError as http_err:
            try:
                j = http_err.response.json()
                st.error(f"Error de API ({http_err.response.status_code}): {j}")
            except Exception:
                st.error(f"Error de API: {http_err}")
        except Exception as e:
            st.error(f"No se pudo obtener datos: {e}")
    else:
        st.info("Escribe un usuario de TikTok (sin @) y pulsa **Consultar**. "
                "Asegúrate de que tu capturador Node esté corriendo.")

    # --- SERIES + SNAPSHOT (3 gráficas)
    if tt_snap is not None:
        st.session_state["tt_hist"] = (st.session_state["tt_hist"] + [tt_snap])[-200:]

    if st.session_state["tt_hist"]:
        df_t = pd.DataFrame(st.session_state["tt_hist"])

        # 1) LÍNEAS con markers (evolución)
        y_cols = [c for c in ["viewers", "likes", "comments", "diamonds"] if c in df_t.columns]
        if y_cols:
            fig_t = px.line(
                df_t, x="ts", y=y_cols,
                title="Evolución en vivo — TikTok",
                color_discrete_map={
                    "viewers": PLATFORM_COLORS["TikTok"],
                    "likes": "#22c55e",
                    "comments": "#fbbf24",
                    "diamonds": "#a855f7",
                },
                markers=True,
            )
            fig_t.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")
            st.plotly_chart(fig_t, use_container_width=True)

            # DF del último snapshot
            row = df_t.iloc[-1]
            df_t_last = pd.DataFrame({
                "metric": [m for m in y_cols],
                "value":  [int(row.get(m, 0)) for m in y_cols]
            })
            color_map_t = {
                "viewers": PLATFORM_COLORS["TikTok"],
                "likes": "#22c55e",
                "comments": "#fbbf24",
                "diamonds": "#a855f7",
            }

            # 2) BARRAS + 3) DONUT
            cb1, cb2 = st.columns(2)
            fig_bar_t, fig_pie_t = _bar_and_pie_from_last(df_t_last, "TikTok", color_map_t)
            cb1.plotly_chart(fig_bar_t, use_container_width=True)
            cb2.plotly_chart(fig_pie_t, use_container_width=True)

st.caption("Consejo: ID/URL de YouTube usa del video; TikTok lee un JSON que escribe tu script Node. Asegúrate de correr ambos.")

def render_youtube_tab(tab_container, DEFAULT_VIDEO_ID=""):
    with tab_container:
        st.subheader("YouTube en vivo")
        if "yt_q" not in st.session_state:
            st.session_state["yt_q"] = ""
        if "yt_run" not in st.session_state:
            st.session_state["yt_run"] = False
        st.session_state.setdefault("yt_hist", [])
        q = st.text_input(
            "Pega la URL o ID de un video en vivo (también acepta youtu.be).",
            value=DEFAULT_VIDEO_ID,
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID o VIDEO_ID",
            key="yt_input_v2",
        )
        colA, colB, colC = st.columns([1, 1, 2])
        run_click = colA.button("Consultar", type="primary", key="yt_btn_v2")
        yt_auto   = colB.toggle("Auto-actualizar 3s", value=True, key="yt_auto_v2")
        yt_debug  = colC.toggle("Debug", value=False, key="yt_dbg_v2")
        if run_click and q:
            st.session_state["yt_q"] = q
            st.session_state["yt_run"] = True
            st.session_state["yt_hist"] = []
        raw_query = st.session_state.get("yt_q", "")
        video_id = yt_normalize_id(raw_query)
        st.caption(f"Backend: {LOCAL_API} — Consultando video_id: {video_id or '—'}")
        if yt_auto and st.session_state.get("yt_run") and video_id:
            st_autorefresh(interval=3000, key="yt_live_auto_v2")
        st.subheader("📊 Métricas en vivo")
        yt_snap = None
        dbg_raw = None
        if st.session_state.get("yt_run") and video_id:
            try:
                ok, data, status = api_get_debug("/live-data", params={"video": video_id})
                dbg_raw = {"ok": ok, "status": status, "payload": data}
                items = []
                if isinstance(data, dict):
                    if isinstance(data.get("items"), list):
                        items = data.get("items")
                    else:
                        items = [data]
                if not ok:
                    st.error(f"Backend respondió con estado {status}. Revisa el Debug para ver detalles.")
                elif not items:
                    st.warning("No se recibieron datos del live (¿está realmente en vivo? ¿API key válida?).")
                else:
                    node = items[0] or {}
                    stats = (node.get("statistics") or {}) if isinstance(node, dict) else {}
                    live  = (node.get("liveStreamingDetails") or {}) if isinstance(node, dict) else {}
                    view_count   = int(stats.get("viewCount") or node.get("viewCount") or 0)
                    like_count   = int(stats.get("likeCount") or node.get("likeCount") or 0)
                    concurrent   = int(live.get("concurrentViewers") or stats.get("concurrentViewers") or node.get("concurrentViewers") or 0)
                    live_comments = int(node.get("liveCommentCount") or stats.get("liveCommentCount") or 0)
                    if not live_comments:
                        live_comments = int(len(data.get("comentarios", []))) if isinstance(data, dict) else 0
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("👀 Vistas", f"{view_count}")
                    c2.metric("👍 Me gusta", f"{like_count}")
                    c3.metric("🟢 Concurrentes", f"{concurrent}")
                    c4.metric("💬 Comentarios (live)", f"{live_comments}")
                    st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")
                    yt_snap = {
                        "ts": pd.Timestamp.utcnow(),
                        "views": concurrent or view_count,
                        "likes": like_count,
                        "comments": live_comments,
                    }
            except Exception as e:
                st.error(f"No se pudo obtener datos: {e}")
        else:
            st.info("Pega una URL/ID de un video en vivo y presiona **Consultar**.")
        if yt_debug and dbg_raw is not None:
            with st.expander("🔎 Debug de respuesta de la API"):
                st.json(dbg_raw)
        if yt_snap is not None:
            st.session_state["yt_hist"] = (st.session_state["yt_hist"] + [yt_snap])[-200:]
        if st.session_state["yt_hist"]:
            df_y = pd.DataFrame(st.session_state["yt_hist"])
            fig_y = px.line(
                df_y, x="ts", y=["views", "likes", "comments"],
                title="Evolución en vivo — YouTube",
                markers=True,
            )
            fig_y.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")
            st.plotly_chart(fig_y, use_container_width=True)
            row = df_y.iloc[-1]
            df_y_last = pd.DataFrame({
                "metric": ["views", "likes", "comments"],
                "value":  [int(row.get("views", 0)), int(row.get("likes", 0)), int(row.get("comments", 0))]
            })
            cb1, cb2 = st.columns(2)
            fig_bar = px.bar(df_y_last, x="metric", y="value", text="value", title="YouTube — snapshot (barras)")
            fig_bar.update_traces(textposition="outside", cliponaxis=False)
            fig_bar.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, showlegend=False)
            cb1.plotly_chart(fig_bar, use_container_width=True)
            fig_pie = px.pie(df_y_last, names="metric", values="value", hole=0.55, title="YouTube — snapshot (donut)")
            fig_pie.update_traces(textposition="inside", texttemplate='%{percent:.1%}')
            fig_pie.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320)
            cb2.plotly_chart(fig_pie, use_container_width=True)

render_youtube_tab(tab_yt, DEFAULT_VIDEO_ID if 'DEFAULT_VIDEO_ID' in globals() else '')