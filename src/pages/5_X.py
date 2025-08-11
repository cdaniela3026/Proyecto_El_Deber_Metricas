import streamlit as st, pandas as pd
from pathlib import Path
from datetime import timedelta
from utils.charts import branded_line, brand_color
from utils.formatting import trend_card, inject_css
st.set_page_config(page_title="✖️ X (Twitter)", layout="wide")
BASE_DIR=Path(__file__).resolve().parents[2]; DATA_DIR=BASE_DIR/'data'/'sample'; PLATFORM="X"
df=pd.read_csv(DATA_DIR/'sample_posts.csv', parse_dates=['date']); df=df[df['platform']==PLATFORM]
if df.empty: st.info('Sin datos de X.'); st.stop()
min_d,max_d=df['date'].min().date(), df['date'].max().date(); default_from=max(min_d, max_d - timedelta(days=30))
st.sidebar.subheader('Filtros X'); f=st.sidebar.date_input('Desde', default_from, min_value=min_d, max_value=max_d); t=st.sidebar.date_input('Hasta', max_d, min_value=min_d, max_value=max_d)
df_now=df[(df['date'].dt.date>=f)&(df['date'].dt.date<=t)]
accent=brand_color(PLATFORM); inject_css(accent)
st.header('✖️ X (Twitter)'); st.caption('Datos de muestra — luego conectamos API oficial.')
c1,c2,c3=st.columns(3); trend_card(c1,'Publicaciones', int(df_now['posts'].sum()), accent=accent); trend_card(c2,'Vistas', int(df_now['views'].sum()), accent=accent); trend_card(c3,'Interacciones', int(df_now['interactions'].sum()), accent=accent)
st.markdown('### Vistas por día'); ts=df_now.groupby('date',as_index=False)['views'].sum(); fig=branded_line(ts,'date','views','Vistas por día', single_platform=PLATFORM); st.plotly_chart(fig,use_container_width=True)
st.subheader('Detalle'); st.dataframe(df_now.sort_values('date', ascending=False), use_container_width=True)
