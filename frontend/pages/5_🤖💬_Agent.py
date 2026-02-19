"""
AI Agent 对话页面 — ChatGPT 风格布局
左侧可收缩会话导航 + 右侧聊天区域
"""
import streamlit as st
import requests
import uuid
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Agent", page_icon="🤖💬", layout="wide")

# 不调用 language_selector()，避免往 sidebar 写内容（否则会产生可展开分割线）
# 语言切换放到页面内部顶栏
from i18n import init_language
init_language()

# =============================================
# CSS — ChatGPT 风格: 深色左栏 + 去掉侧边栏分割线
# =============================================
st.markdown("""
<style>
/* ---- 隐藏 sidebar 里导航之后的所有多余内容（可展开线等） ---- */

/* ---- 左侧会话面板样式 (深色主题) ---- */
.conv-panel {
    background: #1a1a2e;
    border-radius: 12px;
    padding: 12px;
    height: calc(100vh - 140px);
    overflow-y: auto;
    color: #e0e0e0;
}
.conv-panel::-webkit-scrollbar {
    width: 4px;
}
.conv-panel::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 4px;
}

/* 新对话按钮 */
.new-conv-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 10px 12px;
    background: #2d2d44;
    border: 1px dashed #555;
    border-radius: 8px;
    color: #e0e0e0;
    font-size: 14px;
    cursor: pointer;
    margin-bottom: 12px;
    transition: background 0.2s;
}
.new-conv-btn:hover {
    background: #3d3d5c;
}

/* 单条对话记录 */
.conv-item {
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 4px;
    cursor: pointer;
    transition: background 0.2s;
    color: #ccc;
    font-size: 13px;
    line-height: 1.4;
    border: 1px solid transparent;
}
.conv-item:hover {
    background: #2d2d44;
}
.conv-item.active {
    background: #2d2d44;
    border-color: #FF6B35;
    color: #fff;
}
.conv-item .conv-title {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
}
.conv-item .conv-meta {
    font-size: 11px;
    color: #888;
    margin-top: 2px;
}

/* 面板标题 */
.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 4px 8px;
    border-bottom: 1px solid #333;
    margin-bottom: 10px;
}
.panel-title {
    font-size: 13px;
    font-weight: 600;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* 聊天区域 */
.chat-area {
    height: calc(100vh - 140px);
    display: flex;
    flex-direction: column;
}

/* 切换按钮 */
.toggle-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 1px solid #ddd;
    background: #fafafa;
    cursor: pointer;
    font-size: 18px;
    transition: all 0.2s;
    margin-bottom: 8px;
}
.toggle-btn:hover {
    background: #eee;
    border-color: #bbb;
}

/* 空状态 */
.empty-conv {
    text-align: center;
    color: #666;
    padding: 30px 10px;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


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

# 顶栏: 汉堡按钮 + 标题 + 语言切换
toggle_col, title_col, lang_col = st.columns([0.04, 0.82, 0.14])
with toggle_col:
    if st.button("☰", key="toggle_panel", help=t("agent_toggle_panel")):
        st.session_state.show_conv_panel = not st.session_state.show_conv_panel
        st.rerun()

with title_col:
    st.markdown(f"### {t('agent_title')}")

with lang_col:
    lang = st.radio(
        "🌐",
        options=["zh", "en"],
        format_func=lambda x: "中文" if x == "zh" else "EN",
        index=0 if st.session_state.get("lang", "zh") == "zh" else 1,
        key="agent_lang_radio",
        horizontal=True,
        label_visibility="collapsed",
    )
    if lang != st.session_state.get("lang", "zh"):
        st.session_state.lang = lang
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
            st.markdown(
                f"<div class='empty-conv'>{t('agent_no_conversations')}</div>",
                unsafe_allow_html=True,
            )

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
