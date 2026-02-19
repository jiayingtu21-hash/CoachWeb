"""
模型训练页面
选择数据 → 训练 → 查看结果 → 下载模型
"""
import streamlit as st
import requests
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
import numpy as np
from i18n import language_selector, t

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Train", page_icon="🤖", layout="wide")
language_selector()
st.title(t("train_title"))


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path, json_data):
    try:
        r = requests.post(f"{API_URL}{path}", json=json_data, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"{t('request_failed')}: {e}")
        return None


# ---- 加载 Sessions ----
sessions_data = api_get("/api/sessions/list")
if not sessions_data or not sessions_data.get("sessions"):
    st.info(t("no_data_upload_short"))
    st.stop()

sessions = sessions_data["sessions"]

# ---- Step 1: 选择训练数据 ----
st.subheader(t("select_training_data"))

session_options = {}
for s in sessions:
    label = f"{s['name']} (Good:{s.get('good_count',0)} Bad:{s.get('bad_count',0)})"
    session_options[label] = s["id"]

selected = st.multiselect(
    t("select_sessions_multi"),
    options=list(session_options.keys()),
    default=list(session_options.keys())
)
selected_ids = [session_options[name] for name in selected]

if selected:
    total_good = sum(s.get('good_count', 0) for s in sessions if s['id'] in selected_ids)
    total_bad = sum(s.get('bad_count', 0) for s in sessions if s['id'] in selected_ids)
    c1, c2, c3 = st.columns(3)
    c1.metric(t("selected_sessions"), len(selected_ids))
    c2.metric(t("good_samples"), total_good)
    c3.metric(t("bad_samples"), total_bad)

    if total_good == 0 or total_bad == 0:
        st.warning(t("need_both"))

st.markdown("---")

# ---- Step 2: 模型配置 ----
st.subheader(t("model_config"))

model_type_names = {"svm": t("svm_name"), "decision_tree": t("dt_name"), "random_forest": t("rf_name")}

col1, col2 = st.columns(2)

with col1:
    model_type = st.selectbox(
        t("model_type"),
        ["svm", "decision_tree", "random_forest"],
        format_func=lambda x: model_type_names[x]
    )

with col2:
    if model_type == "svm":
        svm_c = st.slider(t("regularization"), 0.01, 10.0, 1.0, step=0.1)
        svm_kernel = st.selectbox("Kernel", ["rbf", "linear", "poly"])
        max_depth = None
        n_estimators = 100
    elif model_type == "decision_tree":
        max_depth = st.slider("Max Depth", 1, 20, 5)
        svm_c = 1.0
        svm_kernel = "rbf"
        n_estimators = 100
    else:
        n_estimators = st.slider(t("tree_count"), 10, 500, 100, step=10)
        max_depth = st.slider(t("max_depth_label"), 0, 20, 5)
        if max_depth == 0:
            max_depth = None
        svm_c = 1.0
        svm_kernel = "rbf"

st.markdown("---")

# ---- Step 3: 开始训练 ----
st.subheader(t("training_section"))

if st.button(t("start_training"), type="primary", use_container_width=True, disabled=not selected_ids):
    with st.spinner(t("training_progress")):
        result = api_post("/api/training/start", {
            "session_ids": selected_ids,
            "model_type": model_type,
            "svm_c": svm_c,
            "svm_kernel": svm_kernel,
            "max_depth": max_depth,
            "n_estimators": n_estimators,
        })

    if result and result.get("status") == "completed":
        st.success(t("training_complete"))
        st.session_state["last_training_result"] = result
    elif result:
        st.error(f"{t('training_failed')}: {result}")

# ---- Step 4: 显示结果 ----
result = st.session_state.get("last_training_result")
if result:
    st.markdown("---")
    st.subheader(t("results_section"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("accuracy"), f"{result['accuracy']:.1%}")
    c2.metric(t("precision"), f"{result['precision']:.1%}")
    c3.metric(t("recall"), f"{result['recall']:.1%}")
    c4.metric(t("f1_score"), f"{result['f1_score']:.1%}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{t('cross_val')}**")
        st.write(f"{t('cv_mean')}: {result['cv_mean']:.1%} ± {result['cv_std']:.1%}")
        st.write(f"{t('sample_count')}: {result['sample_count']}")

    with col2:
        st.markdown(f"**{t('confusion_matrix')}**")
        cm = result.get("confusion_matrix", [])
        labels = result.get("labels", ["bad", "good"])
        if cm:
            cm_array = np.array(cm)
            fig_cm = go.Figure(data=go.Heatmap(
                z=cm_array,
                x=labels,
                y=labels,
                text=cm_array,
                texttemplate="%{text}",
                colorscale="Blues",
            ))
            fig_cm.update_layout(
                xaxis_title=t("predicted"),
                yaxis_title=t("actual"),
                height=300,
            )
            st.plotly_chart(fig_cm, use_container_width=True)

    # 下载按钮
    run_id = result.get("run_id")
    if run_id:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if result.get("coreml_exported"):
                st.markdown(f"**{t('download_coreml')}**")
                st.markdown(f"[{t('click_download')} tennis_model_{run_id}.mlmodel]({API_URL}/api/training/download/{run_id}?fmt=mlmodel)")
            else:
                st.info(t("coreml_not_exported"))
        with col2:
            st.markdown(f"**{t('download_pkl')}**")
            st.markdown(f"[{t('click_download')} tennis_model_{run_id}.pkl]({API_URL}/api/training/download/{run_id}?fmt=pkl)")

st.markdown("---")

# ---- 训练历史 ----
st.subheader(t("training_history"))
runs_data = api_get("/api/training/runs")
if runs_data and runs_data.get("runs"):
    for run in reversed(runs_data["runs"]):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**{run['run_id']}**")
            c2.write(f"{t('model_label')}: {run['model_type']}")
            c3.write(f"{t('accuracy_label')}: {run['accuracy']:.1%}")
            c4.write(f"{t('samples_label')}: {run['sample_count']}")
else:
    st.info(t("no_training_history"))
