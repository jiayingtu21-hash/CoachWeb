"""
数据可视化页面
IMU 时序图 + Feedback 散点图
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Visualize", page_icon="📈", layout="wide")
language_selector()
st.title(t("viz_title"))


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ---- 加载 Sessions ----
sessions_data = api_get("/api/sessions/list")
if not sessions_data or not sessions_data.get("sessions"):
    st.info(t("no_data_upload"))
    st.stop()

sessions = sessions_data["sessions"]
session_options = {s["name"]: s["id"] for s in sessions}

# ---- Session 选择 ----
selected_names = st.multiselect(
    t("select_sessions"),
    options=list(session_options.keys()),
    default=[list(session_options.keys())[0]] if session_options else []
)

if not selected_names:
    st.warning(t("select_one"))
    st.stop()

# ---- 显示控制 ----
col1, col2 = st.columns(2)
with col1:
    show_axes = st.multiselect(
        t("show_axes"),
        ["AccX", "AccY", "AccZ", "AccMag", "GyroX", "GyroY", "GyroZ"],
        default=["AccMag"]
    )
with col2:
    sample_rate = st.slider(t("downsample"), 0, 5000, 2000, step=500)

# 轴名称到 CSV 列名的映射
axis_map = {
    "AccX": "userAccelX", "AccY": "userAccelY", "AccZ": "userAccelZ",
    "AccMag": "accMag",
    "GyroX": "rotationRateX", "GyroY": "rotationRateY", "GyroZ": "rotationRateZ",
}

# ---- 颜色 ----
colors = ["#FF6B35", "#1E90FF", "#32CD32", "#FF1493", "#FFD700", "#8A2BE2"]

# ---- IMU 时序图 ----
st.subheader(t("imu_chart"))

fig = make_subplots(rows=1, cols=1)

for i, name in enumerate(selected_names):
    sid = session_options[name]
    params = {"sample_rate": sample_rate} if sample_rate > 0 else {}
    raw = api_get(f"/api/viz/raw-data/{sid}?sample_rate={params.get('sample_rate', '')}")
    if not raw or not raw.get("data"):
        st.warning(f"Session '{name}' {t('no_raw_data')}")
        continue

    df = pd.DataFrame(raw["data"])

    # 优先用 seconds_elapsed 作为 x 轴
    time_col = "seconds_elapsed" if "seconds_elapsed" in df.columns else "time"

    for ax in show_axes:
        col_name = axis_map.get(ax)
        if col_name and col_name in df.columns:
            color = colors[i % len(colors)]
            label = f"{name} - {ax}" if len(selected_names) > 1 else ax
            fig.add_trace(go.Scatter(
                x=df[time_col],
                y=df[col_name],
                mode='lines',
                name=label,
                line=dict(width=1),
            ))

# 在时序图上叠加峰值标记
show_peaks = st.checkbox(t("show_peaks"), value=True)
if show_peaks:
    for i, name in enumerate(selected_names):
        sid = session_options[name]
        fb = api_get(f"/api/viz/feedback-data/{sid}")
        raw_for_peaks = api_get(f"/api/viz/raw-data/{sid}?sample_rate=1")
        if fb and fb.get("actions") and raw_for_peaks and raw_for_peaks.get("data"):
            # 计算 time 基准，将 t_peak 转换为 seconds_elapsed
            first_row = raw_for_peaks["data"][0]
            uses_seconds = "seconds_elapsed" in first_row
            base_time = float(first_row.get("time", 0)) if uses_seconds else 0

            for action in fb["actions"]:
                t_peak = action.get("t_peak")
                if uses_seconds and base_time > 0:
                    x_val = t_peak - base_time
                else:
                    x_val = t_peak
                quality = action.get("manual_quality", "")
                color = {"good": "rgba(50,205,50,0.4)", "bad": "rgba(255,68,68,0.4)"}.get(quality, "rgba(150,150,150,0.3)")
                fig.add_vline(x=x_val, line_dash="dot", line_color=color, line_width=1)

fig.update_layout(
    height=500,
    xaxis_title=t("time_sec"),
    yaxis_title=t("value"),
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.2),
)
st.plotly_chart(fig, use_container_width=True)

# ---- Feedback 散点图 ----
st.subheader(t("quality_scatter"))

for i, name in enumerate(selected_names):
    sid = session_options[name]
    fb = api_get(f"/api/viz/feedback-data/{sid}")
    if not fb or not fb.get("actions"):
        continue

    actions = fb["actions"]
    df_fb = pd.DataFrame(actions)

    if len(selected_names) > 1:
        st.markdown(f"**{name}**")

    # 颜色映射
    color_map = {"good": "#32CD32", "bad": "#FF4444", "unlabeled": "#999999"}

    fig_fb = go.Figure()

    for quality in ["good", "bad", "unlabeled"]:
        if "manual_quality" in df_fb.columns:
            subset = df_fb[df_fb["manual_quality"] == quality]
        else:
            subset = pd.DataFrame()
        if len(subset) > 0:
            fig_fb.add_trace(go.Scatter(
                x=subset["action_index"],
                y=[quality] * len(subset),
                mode='markers',
                name=quality.capitalize(),
                marker=dict(
                    size=12,
                    color=color_map.get(quality, "#999"),
                    symbol="circle",
                ),
                text=[f"Peak: {row.get('t_peak', 'N/A')}" for _, row in subset.iterrows()],
                hovertemplate="Action %{x}<br>%{text}<extra></extra>",
            ))

    fig_fb.update_layout(
        height=250,
        xaxis_title=t("action_index"),
        yaxis_title=t("quality"),
        showlegend=True,
        legend=dict(orientation="h", y=-0.3),
    )
    st.plotly_chart(fig_fb, use_container_width=True)

    # 统计表
    if "manual_quality" in df_fb.columns:
        counts = df_fb["manual_quality"].value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("Good", counts.get("good", 0))
        c2.metric("Bad", counts.get("bad", 0))
        c3.metric("Unlabeled", counts.get("unlabeled", 0))
