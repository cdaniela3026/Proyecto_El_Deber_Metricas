import plotly.express as px
platform_colors={'Facebook':'#1877F2','Instagram':'#E1306C','TikTok':'#69C9D0','X':'#000000','YouTube':'#FF0000','Web':'#16a34a'}
def brand_color(n, default='#16a34a'): return platform_colors.get(n, default)
def branded_bar(df,x,y,category_col,title=''):
    fig=px.bar(df,x=x,y=y,title=title,template='plotly_dark',color=category_col,color_discrete_map=platform_colors,category_orders={category_col:list(platform_colors.keys())},text=y)
    fig.update_traces(texttemplate='%{text:,}', textposition='outside', cliponaxis=False); fig.update_layout(margin=dict(l=10,r=10,t=40,b=10)); return fig
def branded_line(df,x,y,title='',single_platform=None):
    if single_platform: fig=px.line(df,x=x,y=y,title=title,template='plotly_dark',color_discrete_sequence=[brand_color(single_platform)])
    else: fig=px.line(df,x=x,y=y,title=title,template='plotly_dark')
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10)); return fig
def world_choropleth(df, code_col='iso3', value_col='value', title='Mapa de calor'):
    fig=px.choropleth(df, locations=code_col, color=value_col, color_continuous_scale='Blues', projection='natural earth', template='plotly_dark', title=title)
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0)); return fig
