import streamlit as st
DEFAULT_ACCENT='#16a34a'
def inject_css(accent: str = DEFAULT_ACCENT):
    st.markdown(f"""<style>
    .metric-card{{background:#0f172a;padding:16px;border-radius:18px;box-shadow:0 10px 30px rgba(0,0,0,.35);border:1px solid {accent}55;}}
    .metric-card h3{{margin:0 0 6px 0;font-size:.9rem;color:#9ca3af;font-weight:600;letter-spacing:.2px;}}
    .metric-card .value{{font-size:1.9rem;font-weight:800;color:#e5e7eb;}}
    .metric-card .help{{font-size:.8rem;color:#9ca3af;}}
    </style>""", unsafe_allow_html=True)
def trend_card(container,label,value,delta_pct=None,help_text=None,accent: str = DEFAULT_ACCENT):
    inject_css(accent); color=accent if (delta_pct or 0)>=0 else '#ef4444'; arrow='▲' if (delta_pct or 0)>=0 else '▼'; delta_txt='—' if delta_pct is None else f"{arrow} {abs(delta_pct)*100:.1f}%"
    with container: st.markdown(f"<div class='metric-card' style='border-color:{color}55'><h3>{label}</h3><div class='value'>{value}</div><div class='help' style='color:{color}'>{delta_txt}</div><div class='help'>{help_text or ''}</div></div>", unsafe_allow_html=True)
