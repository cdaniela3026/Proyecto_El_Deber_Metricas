# src/pages/00_Visión_general.py — Panel de visión general (con KPIs + colores de marca)
import os
import base64
import datetime as dt
import json
import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
import plotly.express as px
import streamlit as st
import time

# -----------------------------
# Config & helpers
# -----------------------------
LOCAL_API = os.getenv("LOCAL_API_BASE", "http://127.0.0.1:8001").rstrip("/")
LOGO_PATH = os.getenv("LOGO_PATH", "assets/el_deber.webp")

# Colores por plataforma (consistentes en todos los gráficos)
PLATFORM_COLORS = {
    "YouTube": "#FF0000",   # rojo
    "TikTok": "#67D6E2",    # cian
    "Instagram": "#FF4F86", # rosa
    "X": "#000000",         # negro
    "Facebook": "#1877F2",  # azul
}

@st.cache_resource
def http_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.4, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "POST"])
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


def _embed_logo_html(path: str) -> str:
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = "png" if path.lower().endswith(".png") else "webp"
            return f'<img src="data:image/{ext};base64,{b64}" alt="EL DEBER" height="80">'
    except Exception:
        pass
    return '<span style="font-weight:800;color:#0a6e3a">EL DEBER</span>'


# -----------------------------
# Datos de ejemplo (por si no hay endpoint aún)
# -----------------------------

def sample_data():
    today = dt.date.today()
    days = pd.date_range(end=today, periods=10, freq="D")
    posts_by_day = pd.DataFrame({
        "date": days,
        "posts": [5, 6, 4, 3, 4, 2, 3, 8, 7, 5],
    })
    geo = pd.DataFrame([
        {"country": "Argentina", "iso3": "ARG", "views": 15000},
        {"country": "Bolivia",   "iso3": "BOL", "views": 25000},
        {"country": "Perú",      "iso3": "PER", "views": 12000},
        {"country": "Chile",     "iso3": "CHL", "views": 8000},
        {"country": "USA",       "iso3": "USA", "views": 5000},
    ])
    share = pd.DataFrame([
        {"platform": "YouTube",  "value": 39.5},
        {"platform": "Instagram","value": 19.1},
        {"platform": "X",        "value": 9.45},
        {"platform": "Facebook", "value": 5.84},
        {"platform": "TikTok",   "value": 26.1},
    ])
    views_by_plat = pd.DataFrame([
        {"platform": "Facebook", "views": 17000},
        {"platform": "Instagram","views": 55500},
        {"platform": "TikTok",   "views": 76000},
        {"platform": "X",        "views": 27500},
        {"platform": "YouTube",  "views": 110000},
    ])
    table = pd.DataFrame([
        {"platform": "YouTube",  "posts": 5,  "interactions": 155000, "views": 110000},
        {"platform": "TikTok",   "posts": 12, "interactions": 78000,  "views": 76000},
        {"platform": "Instagram","posts": 15, "interactions": 51600,  "views": 55500},
        {"platform": "X",        "posts": 9,  "interactions": 17000,  "views": 27500},
        {"platform": "Facebook", "posts": 7,  "interactions": 8800,   "views": 17000},
    ])
    return posts_by_day, geo, share, views_by_plat, table


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Visión general — EL DEBER", layout="wide")

# Estilos: tarjetas para st.metric y ajustes de espaciado
st.markdown(
    """
    <style>
      /* estilo de 'cards' alrededor de cada métrica */
      div[data-testid="stMetric"] {
        background: rgba(2, 6, 23, 0.6);      /* dark glass */
        border: 1px solid rgba(16, 185, 129, .25); /* verde suave */
        border-radius: 12px;
        padding: 16px 18px;
      }
      /* separaciones verticales sutiles */
      section[data-testid="stSidebar"] + div [data-testid="stMetric"] { margin-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header con logo + título + subtítulo
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:1rem;margin:0 0 .5rem 0;">
      {_embed_logo_html(LOGO_PATH)}
      <div>
        <div style="font-size:2rem;font-weight:800;">Cuadro Analítico - El Deber</div>
        <div style="opacity:.75;">Tema dark + acentos por red.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Filtros de fecha
colf1, colf2, colf3 = st.columns([1,1,6])
def_start = dt.date.today() - dt.timedelta(days=29)
def_end = dt.date.today()
start = colf1.date_input("Desde", value=def_start)
end   = colf2.date_input("Hasta", value=def_end)
use_sample = colf3.toggle("Usar datos de ejemplo si no hay API", value=True)

# Carga de datos
posts_by_day = geo = share = views_by_plat = table = None
try:
    data = api_get("/overview", params={"from": start.isoformat(), "to": end.isoformat()})
    # Se espera un JSON con claves: posts_by_day, geo, share, views_by_platform, table
    if isinstance(data, dict) and all(k in data for k in ["posts_by_day", "geo", "share", "views_by_platform", "table"]):
        posts_by_day = pd.DataFrame(data["posts_by_day"])  # [{date, posts}]
        geo = pd.DataFrame(data["geo"])                    # [{country, iso3, views}]
        share = pd.DataFrame(data["share"])                # [{platform, value}]
        views_by_plat = pd.DataFrame(data["views_by_platform"]) # [{platform, views}]
        table = pd.DataFrame(data["table"])                # [{platform, posts, interactions, views}]
    else:
        raise ValueError("/overview no devolvió el esquema esperado")
except Exception as e:
    if use_sample:
        st.info(f"Usando datos de ejemplo: {e}")
        posts_by_day, geo, share, views_by_plat, table = sample_data()
    else:
        st.error(f"No se pudieron cargar datos: {e}")

# -----------------------------
# KPIs superiores (como tu captura)
# -----------------------------
if all(x is not None for x in [posts_by_day, views_by_plat, table]):
    total_posts = int(posts_by_day["posts"].sum())
    total_views = int(views_by_plat["views"].sum())
    total_inter = int(table.get("interactions", pd.Series([0]*len(table))).sum())
    engagement = round((total_inter / total_views * 100.0) if total_views else 0.0, 2)
    avg_posts_day = round(posts_by_day["posts"].mean(), 1)
    best_plat = views_by_plat.sort_values("views", ascending=False).iloc[0]["platform"]
    rango = f"{start:%d/%m}–{end:%d/%m}"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Publicaciones", f"{total_posts:,}".replace(",","."))
    k2.metric("Vistas",        f"{total_views:,}".replace(",","."))
    k3.metric("Interacciones", f"{total_inter:,}".replace(",","."))
    k4.metric("Engagement rate", f"{engagement:.2f}%")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Prom. posts/día", f"{avg_posts_day}")
    k6.metric("Mejor plataforma", best_plat)
    k7.metric("Tasa interacción", f"{engagement:.2f}%")
    k8.metric("Rango fechas", rango)

st.divider()

# -----------------------------
# Gráficos (colores de marca)
# -----------------------------
if posts_by_day is not None:
    fig = px.line(posts_by_day, x="date", y="posts", markers=True, title="Posts por día")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=0), height=260)
    st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns([1,1])
if geo is not None:
    fig_map = px.choropleth(
        geo,
        locations="iso3",
        color="views",
        hover_name="country",
        title="Focos de calor por vistas",
        color_continuous_scale=["#0B1220", "#1e3a8a", "#2563eb", "#60a5fa", "#93c5fd"],
    )
    fig_map.update_geos(
        projection_type="natural earth",
        showcoastlines=True,
        coastlinecolor="#3a3a3a",
        showcountries=True,
        countrycolor="#3a3a3a",
        showland=True,
        landcolor="#0F172A",
        showocean=True,
        oceancolor="#0B1220",
        lakecolor="#0B1220",
        bgcolor="#0B1220",
    )
    fig_map.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title=dict(text="vistas", font=dict(color="#cbd5e1")),
            tickfont=dict(color="#cbd5e1"),
        ),
    )
    c1.plotly_chart(fig_map, use_container_width=True)

if share is not None:
    fig_pie = px.pie(
        share,
        names="platform",
        values="value",
        hole=0.55,
        title="Participación por red",
        color="platform",
        color_discrete_map=PLATFORM_COLORS,
    )
    fig_pie.update_traces(textposition='inside', texttemplate='%{percent:.1%}')
    fig_pie.update_layout(margin=dict(l=0,r=0,t=40,b=0), height=360, legend_title_text="")
    c2.plotly_chart(fig_pie, use_container_width=True)

if views_by_plat is not None:
    fig_bar = px.bar(
        views_by_plat,
        x="platform",
        y="views",
        text="views",
        title="Por red (período seleccionado)",
        color="platform",
        color_discrete_map=PLATFORM_COLORS,
    )
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_bar.update_layout(margin=dict(l=10,r=10,t=40,b=10), height=360, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

if table is not None:
    table_sorted = table.copy()
    if "views" in table_sorted.columns:
        table_sorted = table_sorted.sort_values("views", ascending=False)
    st.dataframe(table_sorted, use_container_width=True, height=260)

st.caption("Este panel usa /overview en la API. Si aún no existe, se muestran datos de ejemplo (puedes desactivar el toggle).")
