"""
AI Agent 对话页面
左侧可收缩会话导航 + 右侧聊天区域
"""
import streamlit as st
import requests
import uuid
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Agent", page_icon="🤖💬", layout="wide")
language_selector()
st.title(t("agent_title"))


# =============================================
# 辅助函数
# =============================================
def api_post(path, json_data):
    try:
        r = requests.post(f"{API_URL}{path}", json=json_data, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def load_conversations():
    """从后端加载对话列表"""
    result = api_get("/api/agent/conversations")
    if result and result.get("conversations"):
        return result["conversations"]
    return []


def load_history(conversation_id):
    """从后端加载对话历史"""
    result = api_get(f"/api/agent/history/{conversation_id}")
    if result and result.get("messages"):
        return [{"role": m["role"], "content": m["content"]} for m in result["messages"]]
    return []


# =============================================
# Session State 初始化
# =============================================
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())[:12]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "show_conv_panel" not in st.session_state:
    st.session_state.show_conv_panel = True


# =============================================
# 布局: 可收缩侧栏 + 聊天区域
# =============================================

# 切换按钮
if st.button("☰", key="toggle_panel", help=t("agent_toggle_panel")):
    st.session_state.show_conv_panel = not st.session_state.show_conv_panel
    st.rerun()

# 根据面板展开/收缩决定列宽
if st.session_state.show_conv_panel:
    panel_col, chat_col = st.columns([0.22, 0.78], gap="medium")
else:
    panel_col = None
    chat_col = st.columns([1])[0]

# ---- 左侧会话面板 ----
if st.session_state.show_conv_panel and panel_col is not None:
    with panel_col:
        # 新对话按钮
        if st.button(f"＋ {t('agent_new_conversation')}", key="new_conv_btn", use_container_width=True):
            st.session_state.conversation_id = str(uuid.uuid4())[:12]
            st.session_state.chat_history = []
            st.rerun()

        st.caption(t("agent_recent_conversations"))
        st.markdown("---")

        # 加载对话列表
        conversations = load_conversations()

        if conversations:
            for conv in conversations:
                cid = conv.get("conversation_id", "???")
                count = conv.get("message_count", 0)
                last_active = conv.get("last_active", "")
                # 截断 last_active 到分钟
                if last_active and len(last_active) > 16:
                    last_active = last_active[:16]

                # 生成简短标题
                first_msg = conv.get("first_message", "")
                if first_msg and len(first_msg) > 28:
                    first_msg = first_msg[:28] + "..."

                display_title = first_msg if first_msg else f"💬 {cid}"
                is_active = (cid == st.session_state.conversation_id)

                # 每个对话一个按钮
                btn_label = f"{'▸ ' if is_active else ''}{display_title}"
                if st.button(
                    btn_label,
                    key=f"conv_{cid}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    if cid != st.session_state.conversation_id:
                        st.session_state.conversation_id = cid
                        st.session_state.chat_history = load_history(cid)
                        st.rerun()

                st.caption(f"  {count} {t('agent_messages')} · {last_active}")
        else:
            st.info(t("agent_no_conversations_simple"))

# ---- 右侧聊天区域 ----
with chat_col:
    # 当前对话 ID 小标签
    st.caption(f"{t('agent_conversation_id')}: `{st.session_state.conversation_id}`")

    # 欢迎消息（仅在对话为空时显示）
    if not st.session_state.chat_history:
        with st.chat_message("assistant", avatar="🎾"):
            st.markdown(t("agent_welcome"))

    # 渲染历史消息
    for msg in st.session_state.chat_history:
        avatar = "🎾" if msg["role"] == "assistant" else "🧑"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# ---- 聊天输入 (全宽底部) ----
if prompt := st.chat_input(t("agent_input_placeholder")):
    # 立即添加用户消息
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with chat_col:
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
