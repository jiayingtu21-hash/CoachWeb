"""
中英文国际化模块
所有页面通过 get_text() 获取翻译文本
"""
import streamlit as st

TRANSLATIONS = {
    # ---- 通用 ----
    "lang_label": {"zh": "🌐 中文", "en": "🌐 English"},
    "backend_connected": {"zh": "后端已连接", "en": "Backend connected"},
    "backend_disconnected": {"zh": "后端未连接 - 请先启动 FastAPI", "en": "Backend not connected - please start FastAPI first"},
    "no_data_upload": {"zh": "暂无数据，请先上传 CSV 文件", "en": "No data yet. Please upload CSV files first."},
    "no_data_upload_short": {"zh": "暂无数据，请先上传 CSV", "en": "No data yet, please upload CSV first"},
    "request_failed": {"zh": "请求失败", "en": "Request failed"},
    "delete": {"zh": "删除", "en": "Delete"},
    "total": {"zh": "总数", "en": "Total"},
    "status": {"zh": "状态", "en": "Status"},

    # ---- Dashboard ----
    "dashboard_title": {"zh": "🎾 Tennis Coach Dashboard", "en": "🎾 Tennis Coach Dashboard"},
    "projects": {"zh": "📊 项目", "en": "📊 Projects"},
    "sessions": {"zh": "📁 Sessions", "en": "📁 Sessions"},
    "no_projects": {"zh": "暂无项目，去 Projects 页面创建一个吧", "en": "No projects yet. Go to Projects page to create one."},
    "no_sessions": {"zh": "暂无数据，去 DataPipeline 页面上传 CSV", "en": "No data yet. Go to DataPipeline to upload CSV."},
    "quick_stats": {"zh": "📈 快速统计", "en": "📈 Quick Stats"},
    "total_sessions": {"zh": "总 Sessions", "en": "Total Sessions"},
    "total_actions": {"zh": "总动作数", "en": "Total Actions"},
    "upload_first": {"zh": "上传数据后这里会显示统计信息", "en": "Statistics will appear after uploading data."},
    "actions": {"zh": "动作", "en": "Actions"},

    # ---- Projects ----
    "projects_title": {"zh": "📊 项目管理", "en": "📊 Project Management"},
    "create_project": {"zh": "创建新项目", "en": "Create New Project"},
    "project_name": {"zh": "项目名称", "en": "Project Name"},
    "project_name_placeholder": {"zh": "例如：正手训练", "en": "e.g., Forehand Training"},
    "description": {"zh": "描述（可选）", "en": "Description (optional)"},
    "description_placeholder": {"zh": "练习内容和目标...", "en": "Practice content and goals..."},
    "create_btn": {"zh": "创建项目", "en": "Create Project"},
    "create_success": {"zh": "项目创建成功！", "en": "Project created successfully!"},
    "create_failed": {"zh": "创建失败", "en": "Creation failed"},
    "existing_projects": {"zh": "现有项目", "en": "Existing Projects"},
    "no_projects_create": {"zh": "还没有项目，在上面创建一个吧！", "en": "No projects yet. Create one above!"},
    "view_sessions": {"zh": "查看 Sessions", "en": "View Sessions"},

    # ---- DataPipeline ----
    "pipeline_title": {"zh": "📤 数据准备 Pipeline", "en": "📤 Data Preparation Pipeline"},
    "step1_title": {"zh": "Step 1: 上传 CSV 文件", "en": "Step 1: Upload CSV Files"},
    "step1_desc": {"zh": "从 App 导出 **Raw CSV**（IMU 数据）和 **Feedback CSV**（动作标注+特征），可以上传多组。", "en": "Export **Raw CSV** (IMU data) and **Feedback CSV** (action labels + features) from the App."},
    "link_project": {"zh": "关联到项目（可选）", "en": "Link to Project (optional)"},
    "no_project": {"zh": "不关联项目", "en": "No project"},
    "raw_csv": {"zh": "Raw IMU CSV", "en": "Raw IMU CSV"},
    "upload_raw": {"zh": "上传 Raw CSV", "en": "Upload Raw CSV"},
    "feedback_csv": {"zh": "Feedback CSV", "en": "Feedback CSV"},
    "upload_feedback": {"zh": "上传 Feedback CSV", "en": "Upload Feedback CSV"},
    "rows_cols": {"zh": "行", "en": "rows"},
    "samples": {"zh": "个样本", "en": "samples"},
    "parse_failed": {"zh": "解析失败", "en": "Parse failed"},
    "session_name": {"zh": "Session 名称（可选）", "en": "Session Name (optional)"},
    "session_name_placeholder": {"zh": "例如：2月19日正手练习", "en": "e.g., Feb 19 Forehand Practice"},
    "upload_btn": {"zh": "上传到服务器", "en": "Upload to Server"},
    "uploading": {"zh": "上传中...", "en": "Uploading..."},
    "upload_success": {"zh": "上传成功！检测到", "en": "Upload successful! Detected"},
    "upload_failed": {"zh": "上传失败", "en": "Upload failed"},

    "step2_title": {"zh": "Step 2: 预览和筛选样本", "en": "Step 2: Preview and Filter Samples"},
    "select_session": {"zh": "选择 Session 查看样本", "en": "Select Session to View"},
    "no_action_data": {"zh": "该 Session 没有动作数据", "en": "No action data in this Session"},
    "total_samples": {"zh": "总样本", "en": "Total Samples"},
    "active_samples": {"zh": "有效样本", "en": "Active Samples"},
    "deleted_samples": {"zh": "已删除", "en": "Deleted"},
    "sample_list": {"zh": "**样本列表** — 点击查看 IMU 波形，勾选要删除的样本", "en": "**Sample List** — Check samples to delete, click to view waveforms"},
    "select_col": {"zh": "选中", "en": "Select"},
    "index_col": {"zh": "序号", "en": "Index"},
    "peak_time": {"zh": "峰值时间", "en": "Peak Time"},
    "quality": {"zh": "质量", "en": "Quality"},
    "ml_pred": {"zh": "ML预测", "en": "ML Pred"},
    "status_col": {"zh": "状态", "en": "Status"},
    "valid": {"zh": "有效", "en": "Active"},
    "deleted": {"zh": "已删除", "en": "Deleted"},
    "delete_selected": {"zh": "删除选中", "en": "Delete Selected"},
    "deleted_n": {"zh": "已删除", "en": "Deleted"},
    "restore_deleted": {"zh": "恢复已删除", "en": "Restore Deleted"},
    "restored_n": {"zh": "已恢复", "en": "Restored"},
    "save_labels": {"zh": "保存标注修改", "en": "Save Label Changes"},
    "updated_n": {"zh": "已更新", "en": "Updated"},

    "step3_title": {"zh": "Step 3: 样本 IMU 波形预览", "en": "Step 3: Sample IMU Waveform Preview"},
    "select_action": {"zh": "选择动作序号查看波形", "en": "Select Action Index to View Waveform"},
    "action_num": {"zh": "动作", "en": "Action"},
    "time_axis": {"zh": "时间", "en": "Time"},
    "accel_axis": {"zh": "加速度 (m/s²)", "en": "Acceleration (m/s²)"},
    "no_waveform": {"zh": "无法加载该动作的波形数据", "en": "Cannot load waveform data for this action"},

    "step4_title": {"zh": "Step 4: 训练数据就绪检查", "en": "Step 4: Training Data Readiness Check"},
    "data_ready": {"zh": "数据就绪！共 {count} 个有效标注样本 (Good: {good}, Bad: {bad})，可以前往训练页面。", "en": "Data ready! {count} labeled samples (Good: {good}, Bad: {bad}). Go to Train page."},
    "go_train": {"zh": "👉 请在左侧导航栏点击 **🤖 Train** 页面开始训练", "en": "👉 Click **🤖 Train** in the sidebar to start training"},
    "data_insufficient": {"zh": "数据不足，无法训练", "en": "Insufficient data for training"},
    "need_min_samples": {"zh": "至少需要 {n} 个标注样本（当前: {count}）", "en": "Need at least {n} labeled samples (current: {count})"},
    "need_good": {"zh": "缺少 Good 样本", "en": "Missing Good samples"},
    "need_bad": {"zh": "缺少 Bad 样本", "en": "Missing Bad samples"},

    # ---- Visualize ----
    "viz_title": {"zh": "📈 数据可视化", "en": "📈 Data Visualization"},
    "select_sessions": {"zh": "选择 Session（可多选对比）", "en": "Select Sessions (multi-select to compare)"},
    "select_one": {"zh": "请选择至少一个 Session", "en": "Please select at least one Session"},
    "show_axes": {"zh": "显示轴", "en": "Show Axes"},
    "downsample": {"zh": "降采样点数（0=全部）", "en": "Downsample points (0=all)"},
    "imu_chart": {"zh": "IMU 时序图", "en": "IMU Time Series"},
    "show_peaks": {"zh": "显示峰值标记", "en": "Show Peak Markers"},
    "no_raw_data": {"zh": "无 raw 数据", "en": "No raw data"},
    "time_sec": {"zh": "时间 (秒)", "en": "Time (s)"},
    "value": {"zh": "数值", "en": "Value"},
    "quality_scatter": {"zh": "动作质量散点图", "en": "Action Quality Scatter Plot"},
    "action_index": {"zh": "动作序号", "en": "Action Index"},

    # ---- Train ----
    "train_title": {"zh": "🤖 模型训练", "en": "🤖 Model Training"},
    "select_training_data": {"zh": "1. 选择训练数据", "en": "1. Select Training Data"},
    "select_sessions_multi": {"zh": "选择 Sessions（可多选）", "en": "Select Sessions (multi-select)"},
    "selected_sessions": {"zh": "选中 Sessions", "en": "Selected Sessions"},
    "good_samples": {"zh": "Good 样本", "en": "Good Samples"},
    "bad_samples": {"zh": "Bad 样本", "en": "Bad Samples"},
    "need_both": {"zh": "需要同时有 Good 和 Bad 样本才能训练", "en": "Need both Good and Bad samples to train"},
    "model_config": {"zh": "2. 模型配置", "en": "2. Model Configuration"},
    "model_type": {"zh": "模型类型", "en": "Model Type"},
    "svm_name": {"zh": "SVM (支持向量机)", "en": "SVM (Support Vector Machine)"},
    "dt_name": {"zh": "决策树", "en": "Decision Tree"},
    "rf_name": {"zh": "随机森林", "en": "Random Forest"},
    "regularization": {"zh": "C (正则化)", "en": "C (Regularization)"},
    "tree_count": {"zh": "树数量", "en": "Number of Trees"},
    "max_depth_label": {"zh": "Max Depth (0=无限)", "en": "Max Depth (0=unlimited)"},
    "training_section": {"zh": "3. 训练", "en": "3. Train"},
    "start_training": {"zh": "🚀 开始训练", "en": "🚀 Start Training"},
    "training_progress": {"zh": "训练中...", "en": "Training..."},
    "training_complete": {"zh": "训练完成！", "en": "Training complete!"},
    "training_failed": {"zh": "训练失败", "en": "Training failed"},
    "results_section": {"zh": "4. 训练结果", "en": "4. Training Results"},
    "accuracy": {"zh": "准确率", "en": "Accuracy"},
    "precision": {"zh": "精确率", "en": "Precision"},
    "recall": {"zh": "召回率", "en": "Recall"},
    "f1_score": {"zh": "F1 Score", "en": "F1 Score"},
    "cross_val": {"zh": "交叉验证", "en": "Cross Validation"},
    "cv_mean": {"zh": "平均", "en": "Mean"},
    "sample_count": {"zh": "样本数", "en": "Sample Count"},
    "confusion_matrix": {"zh": "混淆矩阵", "en": "Confusion Matrix"},
    "predicted": {"zh": "预测", "en": "Predicted"},
    "actual": {"zh": "实际", "en": "Actual"},
    "download_coreml": {"zh": "下载 CoreML 模型", "en": "Download CoreML Model"},
    "download_pkl": {"zh": "下载 Pickle 模型", "en": "Download Pickle Model"},
    "click_download": {"zh": "点击下载", "en": "Click to download"},
    "coreml_not_exported": {"zh": "CoreML 未导出（需要 coremltools）", "en": "CoreML not exported (requires coremltools)"},
    "training_history": {"zh": "训练历史", "en": "Training History"},
    "no_training_history": {"zh": "还没有训练记录", "en": "No training records yet"},
    "model_label": {"zh": "模型", "en": "Model"},
    "accuracy_label": {"zh": "准确率", "en": "Accuracy"},
    "samples_label": {"zh": "样本", "en": "Samples"},

    # ---- Agent Chat ----
    "agent_title": {"zh": "🤖💬 AI 助手", "en": "🤖💬 AI Agent"},
    "agent_welcome": {
        "zh": "你好！我是你的网球教练 AI 助手。\n\n我可以帮你：\n- 📊 查看数据概览 — \"我有多少数据？\"\n- 🏆 分析训练结果 — \"我最好的模型是什么？\"\n- 📋 查看质量分布 — \"质量分布是怎样的？\"\n- 🎾 获取改进建议 — \"如何提高我的技术？\"\n\n试试看吧！",
        "en": "Hello! I'm your Tennis Coach AI Assistant.\n\nI can help you with:\n- 📊 Data overview — \"How much data do I have?\"\n- 🏆 Training results — \"What was my best model?\"\n- 📋 Quality breakdown — \"Show quality distribution\"\n- 🎾 Coaching advice — \"How can I improve?\"\n\nTry it out!"
    },
    "agent_input_placeholder": {"zh": "输入你的问题...", "en": "Type your question..."},
    "agent_thinking": {"zh": "思考中...", "en": "Thinking..."},
    "agent_error": {"zh": "抱歉，请求失败。请确认后端已启动。", "en": "Sorry, request failed. Please check that the backend is running."},
    "agent_new_conversation": {"zh": "🔄 开始新对话", "en": "🔄 New Conversation"},
    "agent_conversation_id": {"zh": "对话 ID", "en": "Conversation ID"},
}


def init_language():
    """初始化语言设置，在每个页面开头调用"""
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"


def language_selector():
    """在侧边栏显示语言切换按钮"""
    init_language()
    with st.sidebar:
        lang = st.radio(
            "Language / 语言",
            options=["zh", "en"],
            format_func=lambda x: "中文" if x == "zh" else "English",
            index=0 if st.session_state.lang == "zh" else 1,
            key="lang_radio",
            horizontal=True,
        )
        if lang != st.session_state.lang:
            st.session_state.lang = lang
            st.rerun()


def t(key: str, **kwargs) -> str:
    """获取翻译文本"""
    init_language()
    lang = st.session_state.get("lang", "zh")
    text = TRANSLATIONS.get(key, {}).get(lang, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
