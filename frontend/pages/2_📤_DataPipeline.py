"""
数据准备 Pipeline
上传 CSV → 预览样本 → 筛选/删除 → 提交训练数据
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Data Pipeline", page_icon="📤", layout="wide")
st.title("📤 数据准备 Pipeline")


def api_get(path, timeout=10):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path, json_data=None, files=None, data=None, timeout=30):
    try:
        r = requests.post(f"{API_URL}{path}", json=json_data, files=files, data=data, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


# ============================================================
# Step 1: 上传 CSV
# ============================================================
st.subheader("Step 1: 上传 CSV 文件")
st.markdown("从 App 导出 **Raw CSV**（IMU 数据）和 **Feedback CSV**（动作标注+特征），可以上传多组。")

# 项目选择
projects_data = api_get("/api/projects/list")
project_options = {"不关联项目": None}
if projects_data and projects_data.get("projects"):
    for p in projects_data["projects"]:
        project_options[p["name"]] = p["id"]
selected_project = st.selectbox("关联到项目（可选）", options=list(project_options.keys()))
project_id = project_options[selected_project]

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Raw IMU CSV**")
    raw_file = st.file_uploader("上传 Raw CSV", type=["csv"], key="raw_csv")
    if raw_file:
        try:
            raw_df = pd.read_csv(raw_file)
            raw_file.seek(0)
            st.success(f"{len(raw_df)} 行, {len(raw_df.columns)} 列")
        except Exception as e:
            st.error(f"解析失败: {e}")

with col2:
    st.markdown("**Feedback CSV**")
    feedback_file = st.file_uploader("上传 Feedback CSV", type=["csv"], key="feedback_csv")
    if feedback_file:
        try:
            fb_df = pd.read_csv(feedback_file)
            feedback_file.seek(0)
            good_n = len(fb_df[fb_df.get('manual_quality', pd.Series()) == 'good']) if 'manual_quality' in fb_df.columns else 0
            bad_n = len(fb_df[fb_df.get('manual_quality', pd.Series()) == 'bad']) if 'manual_quality' in fb_df.columns else 0
            st.success(f"{len(fb_df)} 个样本 (Good: {good_n}, Bad: {bad_n})")
        except Exception as e:
            st.error(f"解析失败: {e}")

# 上传按钮
if raw_file and feedback_file:
    session_name = st.text_input("Session 名称（可选）", placeholder="例如：2月19日正手练习")
    if st.button("上传到服务器", type="primary", use_container_width=True):
        with st.spinner("上传中..."):
            files = {
                "raw_csv": ("raw.csv", raw_file, "text/csv"),
                "feedback_csv": ("feedback.csv", feedback_file, "text/csv"),
            }
            data = {}
            if project_id:
                data["project_id"] = project_id
            if session_name:
                data["session_name"] = session_name

            r = requests.post(f"{API_URL}/api/sessions/upload", files=files, data=data, timeout=30)
            if r.status_code == 200:
                result = r.json()
                st.success(f"上传成功！检测到 {result.get('action_count', 0)} 个样本")
                st.session_state["uploaded_session_id"] = result["id"]
                st.rerun()
            else:
                st.error(f"上传失败: {r.json().get('detail', r.text)}")

st.markdown("---")

# ============================================================
# Step 2: 选择已有 Session 进行预览和筛选
# ============================================================
st.subheader("Step 2: 预览和筛选样本")

sessions_data = api_get("/api/sessions/list")
if not sessions_data or not sessions_data.get("sessions"):
    st.info("暂无数据，请先上传 CSV 文件")
    st.stop()

sessions = sessions_data["sessions"]
session_options = {f"{s['name']} (Good:{s.get('good_count',0)} Bad:{s.get('bad_count',0)})": s["id"] for s in sessions}

# 如果刚上传了，默认选中
default_idx = 0
if "uploaded_session_id" in st.session_state:
    for i, (label, sid) in enumerate(session_options.items()):
        if sid == st.session_state["uploaded_session_id"]:
            default_idx = i
            break

selected_session_label = st.selectbox(
    "选择 Session 查看样本",
    options=list(session_options.keys()),
    index=default_idx,
)
session_id = session_options[selected_session_label]

# 加载动作列表
actions_data = api_get(f"/api/sessions/{session_id}/actions?include_deleted=true")
if not actions_data or not actions_data.get("actions"):
    st.warning("该 Session 没有动作数据")
    st.stop()

all_actions = actions_data["actions"]
active_actions = [a for a in all_actions if not a.get("is_deleted")]
deleted_actions = [a for a in all_actions if a.get("is_deleted")]

# 统计
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("总样本", len(all_actions))
c2.metric("有效样本", len(active_actions))
good_active = sum(1 for a in active_actions if a["manual_quality"] == "good")
bad_active = sum(1 for a in active_actions if a["manual_quality"] == "bad")
c3.metric("Good", good_active)
c4.metric("Bad", bad_active)
c5.metric("已删除", len(deleted_actions))

st.markdown("---")

# 样本表格 + 预览
st.markdown("**样本列表** — 点击查看 IMU 波形，勾选要删除的样本")

# 构建表格数据
table_data = []
for a in all_actions:
    table_data.append({
        "选中": False,
        "ID": a["id"],
        "序号": a["action_index"],
        "峰值时间": round(a["t_peak"], 3),
        "质量": a["manual_quality"],
        "ML预测": a.get("ml_quality", ""),
        "状态": "已删除" if a.get("is_deleted") else "有效",
    })

df_table = pd.DataFrame(table_data)

# 可编辑表格
edited = st.data_editor(
    df_table,
    column_config={
        "选中": st.column_config.CheckboxColumn("选中", default=False),
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        "序号": st.column_config.NumberColumn("序号", disabled=True),
        "峰值时间": st.column_config.NumberColumn("峰值时间", disabled=True, format="%.3f"),
        "质量": st.column_config.SelectboxColumn("质量", options=["good", "bad", "unlabeled"], required=True),
        "ML预测": st.column_config.TextColumn("ML预测", disabled=True),
        "状态": st.column_config.TextColumn("状态", disabled=True),
    },
    use_container_width=True,
    num_rows="fixed",
    hide_index=True,
)

# 操作按钮行
btn_col1, btn_col2, btn_col3 = st.columns(3)

with btn_col1:
    selected_ids = edited[edited["选中"] == True]["ID"].tolist()
    if st.button(f"删除选中 ({len(selected_ids)} 个)", disabled=len(selected_ids) == 0):
        if selected_ids:
            api_post(f"/api/sessions/{session_id}/actions/delete", json_data=selected_ids)
            st.success(f"已删除 {len(selected_ids)} 个样本")
            st.rerun()

with btn_col2:
    deleted_ids = [a["id"] for a in deleted_actions]
    if st.button(f"恢复已删除 ({len(deleted_ids)} 个)", disabled=len(deleted_ids) == 0):
        if deleted_ids:
            api_post(f"/api/sessions/{session_id}/actions/restore", json_data=deleted_ids)
            st.success(f"已恢复 {len(deleted_ids)} 个样本")
            st.rerun()

with btn_col3:
    # 检测质量标注是否有变更
    quality_changes = []
    for idx, row in edited.iterrows():
        original = all_actions[idx] if idx < len(all_actions) else None
        if original and row["质量"] != original["manual_quality"]:
            quality_changes.append((row["ID"], row["质量"]))

    if st.button(f"保存标注修改 ({len(quality_changes)} 个)", disabled=len(quality_changes) == 0):
        for action_id, new_quality in quality_changes:
            requests.put(
                f"{API_URL}/api/sessions/{session_id}/actions/{action_id}",
                json={"manual_quality": new_quality},
                timeout=5,
            )
        st.success(f"已更新 {len(quality_changes)} 个标注")
        st.rerun()

st.markdown("---")

# ============================================================
# Step 3: 查看单个样本的 IMU 波形
# ============================================================
st.subheader("Step 3: 样本 IMU 波形预览")

action_indices = [a["action_index"] for a in active_actions]
if action_indices:
    selected_action_idx = st.selectbox(
        "选择动作序号查看波形",
        options=action_indices,
        format_func=lambda x: f"动作 #{x} ({next((a['manual_quality'] for a in active_actions if a['action_index'] == x), '?')})"
    )

    window_data = api_get(f"/api/viz/action-window/{session_id}/{selected_action_idx}")
    if window_data and window_data.get("data"):
        wdf = pd.DataFrame(window_data["data"])
        action_info = window_data.get("action", {})

        # 标签显示
        quality = action_info.get("manual_quality", "?")
        quality_color = {"good": "green", "bad": "red"}.get(quality, "gray")
        st.markdown(f"**动作 #{selected_action_idx}** — 质量: :{quality_color}[{quality}]")

        # 画波形
        time_col = [c for c in wdf.columns if c in ("time", "seconds_elapsed")][0] if any(c in wdf.columns for c in ("time", "seconds_elapsed")) else wdf.columns[0]
        fig = go.Figure()

        for col, color, label in [
            ("userAccelX", "#FF6B35", "AccX"),
            ("userAccelY", "#1E90FF", "AccY"),
            ("userAccelZ", "#32CD32", "AccZ"),
            ("accMag", "#FF1493", "AccMag"),
        ]:
            if col in wdf.columns:
                fig.add_trace(go.Scatter(
                    x=wdf[time_col], y=wdf[col],
                    mode='lines', name=label,
                    line=dict(width=1.5, color=color),
                ))

        fig.update_layout(
            height=300,
            xaxis_title="时间",
            yaxis_title="加速度 (m/s²)",
            hovermode="x unified",
            margin=dict(t=10, b=40),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("无法加载该动作的波形数据")

st.markdown("---")

# ============================================================
# Step 4: 训练就绪检查
# ============================================================
st.subheader("Step 4: 训练数据就绪检查")

MIN_SAMPLES = 10  # 最少训练样本数
labeled_count = good_active + bad_active

if labeled_count >= MIN_SAMPLES and good_active > 0 and bad_active > 0:
    st.success(f"数据就绪！共 {labeled_count} 个有效标注样本 (Good: {good_active}, Bad: {bad_active})，可以前往训练页面。")
    st.markdown("👉 请在左侧导航栏点击 **🤖 Train** 页面开始训练")
else:
    reasons = []
    if labeled_count < MIN_SAMPLES:
        reasons.append(f"至少需要 {MIN_SAMPLES} 个标注样本（当前: {labeled_count}）")
    if good_active == 0:
        reasons.append("缺少 Good 样本")
    if bad_active == 0:
        reasons.append("缺少 Bad 样本")
    st.warning(f"数据不足，无法训练：{'; '.join(reasons)}")
