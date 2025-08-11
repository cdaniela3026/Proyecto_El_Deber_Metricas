# src/app.py — YouTube + TikTok (limpio y funcional)
import os
import base64
import datetime as dt
import requests
from requests.adapters import HTTPAdapter, Retry
from dotenv import load_dotenv
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# =========================
# Configuración & Helpers
# =========================
load_dotenv()

LOCAL_API = os.getenv("LOCAL_API_BASE", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_VIDEO_ID = os.getenv("VIDEO_ID", "").strip()


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
    """Llama a la API local: path tipo '/live-data' o '/tiktok-stats'."""
    url = f"{LOCAL_API}{path}"
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


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

# Health de la API local
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

# -------------------------
# TAB 1 — YouTube
# -------------------------
with tab_yt:
    st.subheader("YouTube en vivo")

    # Estado YouTube
    if "yt_q" not in st.session_state:
        st.session_state["yt_q"] = ""
    if "yt_run" not in st.session_state:
        st.session_state["yt_run"] = False

    # Entrada + controles
    q = st.text_input(
        "Pega la URL o ID de un video en vivo (también acepta youtu.be).",
        value=DEFAULT_VIDEO_ID,
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID o VIDEO_ID",
        key="yt_input",
    )

    colA, colB, _ = st.columns([1, 1, 6])
    run_click = colA.button("Consultar", type="primary", key="yt_btn")
    yt_auto = colB.toggle("Auto-actualizar cada 3s", value=True, key="yt_auto")

    if run_click and q:
        st.session_state["yt_q"] = q
        st.session_state["yt_run"] = True

    query = st.session_state.get("yt_q", "")

    # Autorefresh mientras esté activo
    if yt_auto and st.session_state.get("yt_run") and query:
        st_autorefresh(interval=3000, key="yt_live_auto")

    st.subheader("📊 Métricas en vivo")

    if st.session_state.get("yt_run") and query:
        try:
            data = api_get("/live-data", params={"video": query})

            items = data.get("items", []) if isinstance(data, dict) else []
            if not items:
                st.info("No se recibieron datos del live (¿está realmente en vivo?).")
            else:
                stats = (items[0].get("statistics", {}) if items else {}) or {}

                view_count = int(stats.get("viewCount", 0))
                like_count = int(stats.get("likeCount", 0))
                concurrent = int(stats.get("concurrentViewers", 0))
                live_comments = int(stats.get("liveCommentCount", 0))

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("👀 Vistas", f"{view_count}")
                c2.metric("👍 Me gusta", f"{like_count}")
                c3.metric("🟢 Concurrentes", f"{concurrent}")
                c4.metric("💬 Comentarios (live)", f"{live_comments}")

                st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")

        except requests.HTTPError as http_err:
            try:
                j = http_err.response.json()
                st.error(f"Error de API ({http_err.response.status_code}): {j}")
            except Exception:
                st.error(f"Error de API: {http_err}")
        except Exception as e:
            st.error(f"No se pudo obtener datos: {e}")
    else:
        st.info("Pega una URL/ID de un video en vivo y presiona **Consultar**.")

# -------------------------
# TAB 2 — TikTok
# -------------------------
with tab_tt:
    st.subheader("TikTok en vivo")

    # Estado TikTok
    if "tt_user" not in st.session_state:
        st.session_state["tt_user"] = ""
    if "tt_run" not in st.session_state:
        st.session_state["tt_run"] = False

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

    tt_user = st.session_state.get("tt_user", "")

    # Autorefresh independiente
    if tt_auto and st.session_state.get("tt_run") and tt_user:
        st_autorefresh(interval=3000, key="tt_live_auto")

    try:
        # Desactiva fallback para no ver datos del usuario anterior si no existe el JSON del nuevo
        params = {"user": tt_user, "fallback": "0"} if tt_user else None
        data = api_get("/tiktok-stats", params=params)

        if isinstance(data, dict) and data.get("error"):
            st.error(data["error"])
        else:
            items = data.get("items", []) if isinstance(data, dict) else []
            if not items:
                st.info("Sin datos disponibles (¿el script Node está corriendo y escribiendo el JSON?).")
            else:
                info = items[0]
                s = info.get("statistics", {}) or {}

                username = s.get("username", tt_user)
                likes = int(s.get("likes", 0))
                comments = int(s.get("comments", 0))
                viewers = int(s.get("viewers", 0))
                diamonds = int(s.get("diamonds", 0))
                shares = int(s.get("shares", 0))
                gifts_count = int(s.get("giftsCount", 0))

                if username:
                    st.caption(f"Streamer: @{username}")

                d1, d2, d3, d4, d5, d6 = st.columns(6)
                d1.metric("❤️ Me gusta", f"{likes}")
                d2.metric("💬 Comentarios", f"{comments}")
                d3.metric("👀 Espectadores", f"{viewers}")
                d4.metric("💎 Diamantes", f"{diamonds}")
                d5.metric("🔁 Acciones", f"{shares}")
                d6.metric("🎁 Regalos", f"{gifts_count}")

                st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")

    except requests.HTTPError as http_err:
        try:
            j = http_err.response.json()
            st.error(f"Error de API ({http_err.response.status_code}): {j}")
        except Exception:
            st.error(f"Error de API: {http_err}")
    except Exception as e:
        st.error(f"No se pudo obtener datos: {e}")

st.caption("Consejo: ID/URL de YouTube usa del video; TikTok lee un JSON que escribe tu script Node. Asegúrate de correr ambos.")
