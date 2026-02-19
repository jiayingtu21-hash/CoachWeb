"""
Tennis Coach Web - Dashboard 主页
"""
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Tennis Coach",
    page_icon="🎾",
    layout="wide",
)

st.title("🎾 Tennis Coach Dashboard")
st.markdown("---")


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None


# 检查后端连接
health = api_get("/health")
if health:
    st.success("后端已连接 ✓")
else:
    st.error("后端未连接 - 请先启动 FastAPI：`cd backend && uvicorn main:app --reload`")
    st.stop()

# ---- 项目概览 ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 项目")
    projects_data = api_get("/api/projects/list")
    if projects_data and projects_data.get("projects"):
        for proj in projects_data["projects"]:
            with st.container(border=True):
                st.markdown(f"**{proj['name']}**")
                st.caption(f"Sessions: {proj.get('session_count', 0)} | ID: {proj['id']}")
    else:
        st.info("暂无项目，去 Projects 页面创建一个吧")

with col2:
    st.subheader("📁 Sessions")
    sessions_data = api_get("/api/sessions/list")
    if sessions_data and sessions_data.get("sessions"):
        for s in sessions_data["sessions"]:
            with st.container(border=True):
                st.markdown(f"**{s['name']}**")
                good = s.get('good_count', 0)
                bad = s.get('bad_count', 0)
                total = s.get('action_count', 0)
                st.caption(f"动作: {total} | Good: {good} | Bad: {bad}")
    else:
        st.info("暂无数据，去 Upload 页面上传 CSV")

# ---- 快速统计 ----
st.markdown("---")
st.subheader("📈 快速统计")

sessions = sessions_data.get("sessions", []) if sessions_data else []
if sessions:
    total_actions = sum(s.get('action_count', 0) for s in sessions)
    total_good = sum(s.get('good_count', 0) for s in sessions)
    total_bad = sum(s.get('bad_count', 0) for s in sessions)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总 Sessions", len(sessions))
    c2.metric("总动作数", total_actions)
    c3.metric("Good", total_good)
    c4.metric("Bad", total_bad)
else:
    st.info("上传数据后这里会显示统计信息")

st.markdown("---")
st.caption("Tennis Coach Web MVP | Streamlit + FastAPI")
