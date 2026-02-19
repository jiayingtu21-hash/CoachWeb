"""
项目管理页面
"""
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Projects", page_icon="📊", layout="wide")
st.title("📊 项目管理")


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path, json_data=None):
    try:
        r = requests.post(f"{API_URL}{path}", json=json_data, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


def api_delete(path):
    try:
        r = requests.delete(f"{API_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"删除失败: {e}")
        return None


# ---- 创建项目 ----
st.subheader("创建新项目")
with st.form("create_project"):
    name = st.text_input("项目名称", placeholder="例如：正手训练")
    desc = st.text_area("描述（可选）", placeholder="练习内容和目标...")
    submitted = st.form_submit_button("创建项目")
    if submitted and name:
        result = api_post("/api/projects/create", {"name": name, "description": desc})
        if result and result.get("status") == "success":
            st.success(f"项目 '{name}' 创建成功！")
            st.rerun()
        else:
            st.error("创建失败")

st.markdown("---")

# ---- 项目列表 ----
st.subheader("现有项目")
data = api_get("/api/projects/list")
if data and data.get("projects"):
    for proj in data["projects"]:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"### {proj['name']}")
                st.caption(f"ID: {proj['id']} | {proj.get('description', '')}")
            with col2:
                st.metric("Sessions", proj.get('session_count', 0))
            with col3:
                if st.button("删除", key=f"del_{proj['id']}", type="secondary"):
                    api_delete(f"/api/projects/{proj['id']}")
                    st.rerun()

        # 显示关联的 sessions
        proj_detail = api_get(f"/api/projects/{proj['id']}")
        if proj_detail and proj_detail.get("sessions"):
            with st.expander(f"查看 {proj['name']} 的 Sessions"):
                for s in proj_detail["sessions"]:
                    st.write(f"- **{s['name']}** | 动作: {s.get('action_count', 0)} | "
                             f"Good: {s.get('good_count', 0)} | Bad: {s.get('bad_count', 0)}")
else:
    st.info("还没有项目，在上面创建一个吧！")
