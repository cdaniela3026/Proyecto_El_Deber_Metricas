# src/pages/1_Overview.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.charts import branded_bar   # << colores por plataforma
from pathlib import Path
from datetime import timedelta

st.set_page_config(page_title="Overview", layout="wide")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "sample"

st.header("📌 Overview del rendimiento")
st.caption("Resumen general con datos de muestra.")

df = pd.read_csv(DATA_DIR / "sample_posts.csv", parse_dates=["date"])
if df.empty:
    st.warning("No hay datos para mostrar.")
    st.stop()

# Fechas con límites válidos
min_d, max_d = df["date"].min().date(), df["date"].max().date()
default_from = max(min_d, max_d - timedelta(days=30))
date_from = st.sidebar.date_input("Desde", default_from, min_value=min_d, max_value=max_d)
date_to   = st.sidebar.date_input("Hasta",   max_d,       min_value=min_d, max_value=max_d)

mask = (df["date"].dt.date >= date_from) & (df["date"].dt.date <= date_to)
df_now = df[mask]

# Métricas top
c1, c2, c3, c4 = st.columns(4)
c1.metric("Publicaciones", int(df_now["posts"].sum()))
c2.metric("Vistas", int(df_now["views"].sum()))
c3.metric("Interacciones", int(df_now["interactions"].sum()))
eng = (df_now["interactions"].sum() / df_now["views"].sum()) if df_now["views"].sum() else 0
c4.metric("Engagement rate", f"{eng:.2%}")

# Línea de tendencia
st.markdown("### Tendencia de publicaciones")
ts = df_now.groupby("date", as_index=False)["posts"].sum()
st.plotly_chart(
    px.line(ts, x="date", y="posts", title="Posts por día", template="plotly_dark"),
    use_container_width=True
)

# Barras por red con colores oficiales
st.markdown("### Por red (período seleccionado)")
by_plat = df_now.groupby("platform", as_index=False)[["posts","views","interactions"]].sum()

fig_bar = branded_bar(
    by_plat,
    x="platform",
    y="views",
    category_col="platform",
    title="Vistas por red"
)
st.plotly_chart(fig_bar, use_container_width=True)

st.dataframe(by_plat.sort_values("views", ascending=False), use_container_width=True)
