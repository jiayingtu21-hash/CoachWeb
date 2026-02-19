"""
AI Agent 对话页面
"""
import streamlit as st
import requests
import uuid
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Agent", page_icon="🤖💬", layout="wide")
language_selector()
st.title(t("agent_title"))


def api_post(path, json_data):
    try:
        r = requests.post(f"{API_URL}{path}", json=json_data, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ---- 初始化 session state ----
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())[:12]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---- 侧边栏：对话控制 ----
with st.sidebar:
    st.caption(f"{t('agent_conversation_id')}: `{st.session_state.conversation_id}`")
    if st.button(t("agent_new_conversation"), use_container_width=True):
        st.session_state.conversation_id = str(uuid.uuid4())[:12]
        st.session_state.chat_history = []
        st.rerun()

# ---- 欢迎消息（仅在对话为空时显示）----
if not st.session_state.chat_history:
    with st.chat_message("assistant", avatar="🎾"):
        st.markdown(t("agent_welcome"))

# ---- 渲染历史消息 ----
for msg in st.session_state.chat_history:
    avatar = "🎾" if msg["role"] == "assistant" else "🧑"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ---- 聊天输入 ----
if prompt := st.chat_input(t("agent_input_placeholder")):
    # 立即显示用户消息
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    # 调用后端
    with st.chat_message("assistant", avatar="🎾"):
        with st.spinner(t("agent_thinking")):
            result = api_post("/api/agent/chat", {
                "conversation_id": st.session_state.conversation_id,
                "message": prompt,
                "history": st.session_state.chat_history[:-1],
            })

        if result and result.get("content"):
            st.markdown(result["content"])
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result["content"],
            })
        else:
            error_msg = t("agent_error")
            st.error(error_msg)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": error_msg,
            })

    st.rerun()
