"""
数据准备 Pipeline
上传 CSV → 预览样本 → 筛选/删除 → 提交训练数据
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Data Pipeline", page_icon="📤", layout="wide")
language_selector()
st.title(t("pipeline_title"))


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
        st.error(f"{t('request_failed')}: {e}")
        return None


# ============================================================
# Step 1: 上传 CSV
# ============================================================
st.subheader(t("step1_title"))
st.markdown(t("step1_desc"))

# 项目选择
projects_data = api_get("/api/projects/list")
project_options = {t("no_project"): None}
if projects_data and projects_data.get("projects"):
    for p in projects_data["projects"]:
        project_options[p["name"]] = p["id"]
selected_project = st.selectbox(t("link_project"), options=list(project_options.keys()))
project_id = project_options[selected_project]

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**{t('raw_csv')}**")
    raw_file = st.file_uploader(t("upload_raw"), type=["csv"], key="raw_csv")
    if raw_file:
        try:
            raw_df = pd.read_csv(raw_file)
            raw_file.seek(0)
            st.success(f"{len(raw_df)} {t('rows_cols')}, {len(raw_df.columns)} cols")
        except Exception as e:
            st.error(f"{t('parse_failed')}: {e}")

with col2:
    st.markdown(f"**{t('feedback_csv')}**")
    feedback_file = st.file_uploader(t("upload_feedback"), type=["csv"], key="feedback_csv")
    if feedback_file:
        try:
            fb_df = pd.read_csv(feedback_file)
            feedback_file.seek(0)
            good_n = len(fb_df[fb_df.get('manual_quality', pd.Series()) == 'good']) if 'manual_quality' in fb_df.columns else 0
            bad_n = len(fb_df[fb_df.get('manual_quality', pd.Series()) == 'bad']) if 'manual_quality' in fb_df.columns else 0
            st.success(f"{len(fb_df)} {t('samples')} (Good: {good_n}, Bad: {bad_n})")
        except Exception as e:
            st.error(f"{t('parse_failed')}: {e}")

# 上传按钮
if raw_file and feedback_file:
    session_name = st.text_input(t("session_name"), placeholder=t("session_name_placeholder"))
    if st.button(t("upload_btn"), type="primary", use_container_width=True):
        with st.spinner(t("uploading")):
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
                st.success(f"{t('upload_success')} {result.get('action_count', 0)} {t('samples')}")
                st.session_state["uploaded_session_id"] = result["id"]
                st.rerun()
            else:
                st.error(f"{t('upload_failed')}: {r.json().get('detail', r.text)}")

st.markdown("---")

# ============================================================
# Step 2: 选择已有 Session 进行预览和筛选
# ============================================================
st.subheader(t("step2_title"))

sessions_data = api_get("/api/sessions/list")
if not sessions_data or not sessions_data.get("sessions"):
    st.info(t("no_data_upload"))
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
    t("select_session"),
    options=list(session_options.keys()),
    index=default_idx,
)
session_id = session_options[selected_session_label]

# 加载动作列表
actions_data = api_get(f"/api/sessions/{session_id}/actions?include_deleted=true")
if not actions_data or not actions_data.get("actions"):
    st.warning(t("no_action_data"))
    st.stop()

all_actions = actions_data["actions"]
active_actions = [a for a in all_actions if not a.get("is_deleted")]
deleted_actions = [a for a in all_actions if a.get("is_deleted")]

# 统计
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(t("total_samples"), len(all_actions))
c2.metric(t("active_samples"), len(active_actions))
good_active = sum(1 for a in active_actions if a["manual_quality"] == "good")
bad_active = sum(1 for a in active_actions if a["manual_quality"] == "bad")
c3.metric("Good", good_active)
c4.metric("Bad", bad_active)
c5.metric(t("deleted_samples"), len(deleted_actions))

st.markdown("---")

# 样本表格 + 预览
st.markdown(t("sample_list"))

# 构建表格数据
table_data = []
for a in all_actions:
    table_data.append({
        t("select_col"): False,
        "ID": a["id"],
        t("index_col"): a["action_index"],
        t("peak_time"): round(a["t_peak"], 3),
        t("quality"): a["manual_quality"],
        t("ml_pred"): a.get("ml_quality", ""),
        t("status_col"): t("deleted") if a.get("is_deleted") else t("valid"),
    })

df_table = pd.DataFrame(table_data)

# 可编辑表格
edited = st.data_editor(
    df_table,
    column_config={
        t("select_col"): st.column_config.CheckboxColumn(t("select_col"), default=False),
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        t("index_col"): st.column_config.NumberColumn(t("index_col"), disabled=True),
        t("peak_time"): st.column_config.NumberColumn(t("peak_time"), disabled=True, format="%.3f"),
        t("quality"): st.column_config.SelectboxColumn(t("quality"), options=["good", "bad", "unlabeled"], required=True),
        t("ml_pred"): st.column_config.TextColumn(t("ml_pred"), disabled=True),
        t("status_col"): st.column_config.TextColumn(t("status_col"), disabled=True),
    },
    use_container_width=True,
    num_rows="fixed",
    hide_index=True,
)

# 操作按钮行
btn_col1, btn_col2, btn_col3 = st.columns(3)

with btn_col1:
    selected_ids = edited[edited[t("select_col")] == True]["ID"].tolist()
    if st.button(f"{t('delete_selected')} ({len(selected_ids)})", disabled=len(selected_ids) == 0):
        if selected_ids:
            api_post(f"/api/sessions/{session_id}/actions/delete", json_data=selected_ids)
            st.success(f"{t('deleted_n')} {len(selected_ids)}")
            st.rerun()

with btn_col2:
    deleted_ids = [a["id"] for a in deleted_actions]
    if st.button(f"{t('restore_deleted')} ({len(deleted_ids)})", disabled=len(deleted_ids) == 0):
        if deleted_ids:
            api_post(f"/api/sessions/{session_id}/actions/restore", json_data=deleted_ids)
            st.success(f"{t('restored_n')} {len(deleted_ids)}")
            st.rerun()

with btn_col3:
    # 检测质量标注是否有变更
    quality_changes = []
    for idx, row in edited.iterrows():
        original = all_actions[idx] if idx < len(all_actions) else None
        if original and row[t("quality")] != original["manual_quality"]:
            quality_changes.append((row["ID"], row[t("quality")]))

    if st.button(f"{t('save_labels')} ({len(quality_changes)})", disabled=len(quality_changes) == 0):
        for action_id, new_quality in quality_changes:
            requests.put(
                f"{API_URL}/api/sessions/{session_id}/actions/{action_id}",
                json={"manual_quality": new_quality},
                timeout=5,
            )
        st.success(f"{t('updated_n')} {len(quality_changes)}")
        st.rerun()

st.markdown("---")

# ============================================================
# Step 3: 查看单个样本的 IMU 波形
# ============================================================
st.subheader(t("step3_title"))

action_indices = [a["action_index"] for a in active_actions]
if action_indices:
    selected_action_idx = st.selectbox(
        t("select_action"),
        options=action_indices,
        format_func=lambda x: f"{t('action_num')} #{x} ({next((a['manual_quality'] for a in active_actions if a['action_index'] == x), '?')})"
    )

    window_data = api_get(f"/api/viz/action-window/{session_id}/{selected_action_idx}")
    if window_data and window_data.get("data"):
        wdf = pd.DataFrame(window_data["data"])
        action_info = window_data.get("action", {})

        # 标签显示
        quality = action_info.get("manual_quality", "?")
        quality_color = {"good": "green", "bad": "red"}.get(quality, "gray")
        st.markdown(f"**{t('action_num')} #{selected_action_idx}** — {t('quality')}: :{quality_color}[{quality}]")

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
            xaxis_title=t("time_axis"),
            yaxis_title=t("accel_axis"),
            hovermode="x unified",
            margin=dict(t=10, b=40),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(t("no_waveform"))

st.markdown("---")

# ============================================================
# Step 4: 训练就绪检查
# ============================================================
st.subheader(t("step4_title"))

MIN_SAMPLES = 10  # 最少训练样本数
labeled_count = good_active + bad_active

if labeled_count >= MIN_SAMPLES and good_active > 0 and bad_active > 0:
    st.success(t("data_ready", count=labeled_count, good=good_active, bad=bad_active))
    st.markdown(t("go_train"))
else:
    reasons = []
    if labeled_count < MIN_SAMPLES:
        reasons.append(t("need_min_samples", n=MIN_SAMPLES, count=labeled_count))
    if good_active == 0:
        reasons.append(t("need_good"))
    if bad_active == 0:
        reasons.append(t("need_bad"))
    st.warning(f"{t('data_insufficient')}: {'; '.join(reasons)}")
