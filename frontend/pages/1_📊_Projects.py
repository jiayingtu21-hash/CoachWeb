"""
项目管理页面
"""
import streamlit as st
import requests
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Projects", page_icon="📊", layout="wide")
language_selector()
st.title(t("projects_title"))


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
        st.error(f"{t('request_failed')}: {e}")
        return None


def api_delete(path):
    try:
        r = requests.delete(f"{API_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"{t('request_failed')}: {e}")
        return None


# ---- 创建项目 ----
st.subheader(t("create_project"))
with st.form("create_project"):
    name = st.text_input(t("project_name"), placeholder=t("project_name_placeholder"))
    desc = st.text_area(t("description"), placeholder=t("description_placeholder"))
    submitted = st.form_submit_button(t("create_btn"))
    if submitted and name:
        result = api_post("/api/projects/create", {"name": name, "description": desc})
        if result and result.get("status") == "success":
            st.success(t("create_success"))
            st.rerun()
        else:
            st.error(t("create_failed"))

st.markdown("---")

# ---- 项目列表 ----
st.subheader(t("existing_projects"))
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
                if st.button(t("delete"), key=f"del_{proj['id']}", type="secondary"):
                    api_delete(f"/api/projects/{proj['id']}")
                    st.rerun()

        # 显示关联的 sessions
        proj_detail = api_get(f"/api/projects/{proj['id']}")
        if proj_detail and proj_detail.get("sessions"):
            with st.expander(f"{t('view_sessions')} - {proj['name']}"):
                for s in proj_detail["sessions"]:
                    st.write(f"- **{s['name']}** | {t('actions')}: {s.get('action_count', 0)} | "
                             f"Good: {s.get('good_count', 0)} | Bad: {s.get('bad_count', 0)}")
else:
    st.info(t("no_projects_create"))
