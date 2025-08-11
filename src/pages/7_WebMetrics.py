import streamlit as st
import pandas as pd
from pathlib import Path

# Configuración de página
st.set_page_config(page_title="Métricas Web", layout="wide")

# Directorio base y datos
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "sample"

st.header("🌐 Métricas Web")
st.caption("Datos de muestra — Luego conectaremos Google Analytics 4 o Matomo.")

# Cargar datos de ejemplo
df = pd.read_csv(DATA_DIR / "sample_web_metrics.csv", parse_dates=["date"])

# Filtros rápidos
st.sidebar.subheader("Filtros Métricas Web")
date_from = st.sidebar.date_input("Desde", df["date"].min().date())
date_to = st.sidebar.date_input("Hasta", df["date"].max().date())

mask = (df["date"].dt.date >= date_from) & (df["date"].dt.date <= date_to)
df_filtered = df[mask]

# Tarjetas métricas
c1, c2, c3 = st.columns(3)
c1.metric("Sesiones", int(df_filtered["sessions"].sum()))
c2.metric("Usuarios", int(df_filtered["users"].sum()))
c3.metric("Vistas de página", int(df_filtered["pageviews"].sum()))

# Tabla
st.subheader("Detalle diario")
st.dataframe(df_filtered.sort_values("date", ascending=False))
