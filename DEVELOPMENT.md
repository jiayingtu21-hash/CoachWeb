# Tennis Coach Web - 开发文档

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [SQLite 迁移：从 JSON 到 SQLAlchemy](#3-sqlite-迁移从-json-到-sqlalchemy)
4. [DataPipeline 整合页面](#4-datapipeline-整合页面)
5. [API 端点详解](#5-api-端点详解)
6. [构建与运行](#6-构建与运行)
7. [测试记录](#7-测试记录)
8. [Debug 记录](#8-debug-记录)
9. [后续规划：LLM Agent 接入](#9-后续规划llm-agent-接入)

---

## 1. 项目概述

Tennis Coach Web 是网球教练系统的 Web 端，配合 iOS App 使用。iOS App 负责 IMU 数据采集（100Hz）和本地 ML 模型推理，Web 端负责数据管理、可视化、模型训练和导出。

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | Streamlit | 1.30.0 |
| 后端 | FastAPI + Uvicorn | 0.109.0 |
| 数据库 | SQLite + SQLAlchemy ORM | 2.0.25 |
| ML | scikit-learn | - |
| 可视化 | Plotly | - |
| 包管理 | Conda | - |

### 数据流

```
iOS App → 导出 CSV → Web 上传 → SQLite 存储 → 训练 → 模型导出 → iOS App 部署
```

具体流程：
1. iOS App 导出两个 CSV 文件：Raw IMU 数据（6000行/分钟 @100Hz）和 Feedback 数据（每个动作一行，含 40 维特征 + 质量标注）
2. Web 端上传解析后，CSV 原文件存到文件系统，结构化元数据存到 SQLite
3. 用户在 DataPipeline 页面预览、筛选、标注
4. 在 Train 页面选择数据、配置模型、训练
5. 训练产出 `.pkl`（sklearn 模型）和可选的 `.mlmodel`（CoreML 格式）
6. 下载 CoreML 模型部署到 iOS App

---

## 2. 架构设计

### 目录结构

```
tennis-coach-web/
├── backend/
│   ├── main.py                    # FastAPI 入口，版本 2.0.0
│   ├── config.py                  # Pydantic Settings 配置
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy ORM 模型（4 张表）
│   │   └── database.py            # 引擎、Session 工厂、init_db
│   ├── routers/
│   │   ├── sessions.py            # Session + Action CRUD
│   │   ├── projects.py            # Project CRUD
│   │   ├── training.py            # 训练启动 + 历史 + 下载
│   │   └── visualization.py       # Raw 数据 + Feedback + Action 窗口
│   ├── services/
│   │   ├── storage.py             # 数据访问层（SQLite + 文件系统）
│   │   ├── model_trainer.py       # sklearn 训练 + CoreML 导出
│   │   ├── csv_parser.py          # CSV 解析和验证
│   │   └── feature_extractor.py   # 40 维特征提取
│   ├── storage/                   # 运行时数据（gitignore）
│   │   ├── tennis_coach.db        # SQLite 数据库文件
│   │   ├── csv_files/{session_id}/ # CSV 原文件
│   │   └── models/                # 训练产出的模型文件
│   ├── requirements.txt
│   └── generate_test_data.py      # 测试数据生成脚本
├── frontend/
│   ├── app.py                     # Dashboard 主页
│   ├── pages/
│   │   ├── 1_📊_Projects.py       # 项目管理
│   │   ├── 2_📤_DataPipeline.py   # 数据准备（上传+预览+筛选）
│   │   ├── 3_📈_Visualize.py      # IMU 波形可视化
│   │   └── 4_🤖_Train.py          # 模型训练
│   └── requirements.txt
├── environment.yml                # Conda 环境配置
├── start.sh                       # 一键启动脚本
└── .gitignore
```

### 数据库 Schema

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  projects   │     │   sessions   │     │    actions     │
│─────────────│     │──────────────│     │───────────────│
│ id (PK)     │◄──┐ │ id (PK)      │◄──┐ │ id (PK, auto) │
│ name        │   │ │ project_id   │──►│ │ session_id    │──►│
│ description │   │ │ name         │   │ │ action_index  │
│ created_at  │   │ │ session_type │   │ │ t_peak        │
│             │   │ │ raw_rows     │   │ │ t_start       │
│             │   │ │ action_count │   │ │ t_end         │
│             │   │ │ good_count   │   │ │ ml_quality    │
│             │   │ │ bad_count    │   │ │ manual_quality│
│             │   │ │ unlabeled_   │   │ │ features (JSON)│ ← 40 维特征
│             │   │ │   count      │   │ │ is_deleted    │ ← 软删除
│             │   │ │ created_at   │   │ │ created_at    │
│             │   │ └──────────────┘   │ └───────────────┘
│             │   │                     │
│             │   │ ┌────────────────┐  │
│             │   │ │ training_runs  │  │
│             │   │ │────────────────│  │
│             │   └─│ project_id     │  │
│             │     │ id (PK)        │  │
│             │     │ model_type     │  │
│             │     │ hyperparameters│  │
│             │     │ session_ids    │ ← JSON array
│             │     │ accuracy       │
│             │     │ precision      │
│             │     │ recall         │
│             │     │ f1_score       │
│             │     │ cv_mean/std    │
│             │     │ confusion_matrix│
│             │     │ status         │
│             │     │ coreml_exported│
│             │     └────────────────┘
└─────────────┘
```

### 混合存储策略

| 数据类型 | 存储位置 | 原因 |
|---------|---------|------|
| 项目/Session/Action 元数据 | SQLite | 结构化查询、关联关系、未来 Agent SQL 查询 |
| 训练记录 + 评估指标 | SQLite | 历史对比、Agent 分析 |
| Raw IMU CSV 原文件 | 文件系统 | 大文件（6000行/分钟），只读取不查询 |
| 训练产出模型 | 文件系统 | 二进制文件，直接下载 |

---

## 3. SQLite 迁移：从 JSON 到 SQLAlchemy

### 3.1 迁移动机

原先使用 JSON 文件存储：每个 project/session/training_run 各一个 `.json` 文件。存在以下问题：

1. **无法做关联查询** — 比如"哪些 session 属于某个 project"需要遍历所有文件
2. **无法做聚合统计** — 比如"所有 session 的 good/bad 总数"需要逐个读取
3. **不支持事务** — 删除 session 时无法原子性地同时清理关联的 action
4. **无法支持 Agent 工具** — 未来 LLM Agent 需要通过 SQL 查询数据（`query_session_stats`, `compare_models` 等 tool 直接映射为 SQL 查询）

### 3.2 实施步骤

#### Step 1: 创建 SQLAlchemy ORM 模型

**文件**: `backend/db/models.py`

定义了 4 张表的 ORM 模型：

```python
class Base(DeclarativeBase):
    pass

class Project(Base):        # 项目
class Session(Base):        # 训练 Session
class Action(Base):         # 单个动作（从 Feedback CSV 解析）
class TrainingRun(Base):    # 训练记录
```

**关键设计决策**：

- `Action.features` 使用 `Column(JSON)` 存储 40 维特征向量 — SQLite 原生支持 JSON 列，省去了单独的特征表
- `Action.is_deleted` 实现软删除 — 用户删除的样本可以恢复，训练时自动过滤
- `Session` 冗余存储 `good_count`/`bad_count` — 避免每次统计都要 JOIN actions 表
- `TrainingRun.session_ids` 使用 JSON array — 支持多 session 联合训练
- `Project → Session` 使用 `ondelete="SET NULL"` — 删除项目不会级联删除 session
- `Session → Action` 使用 `ondelete="CASCADE"` — 删除 session 自动清理 actions

#### Step 2: 创建数据库初始化模块

**文件**: `backend/db/database.py`

```python
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite 多线程支持
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)  # 自动建表

def get_db():  # FastAPI 依赖注入
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`check_same_thread=False` 是必需的，因为 FastAPI 使用异步处理，数据库连接可能跨线程使用。

#### Step 3: 重写 storage.py

**文件**: `backend/services/storage.py`

将所有函数的第一个参数改为 `db: DBSession`，内部实现从文件读写改为 SQLAlchemy ORM 操作。

主要变化：
- `list_sessions()`: `os.listdir() + json.load()` → `db.query(Session).all()`
- `save_session()`: `json.dump()` → `db.add(Session(...)); db.commit()`
- 新增 `save_actions()`, `soft_delete_actions()`, `restore_actions()`, `get_training_actions()` 等 action 相关函数
- `update_session_counts()` — 重算 session 的 good/bad/unlabeled 数量（删除/恢复 action 后调用）
- CSV 和模型文件操作保持不变（仍用文件系统）

#### Step 4: 更新 model_trainer.py

**文件**: `backend/services/model_trainer.py`

**改动 1**: 数据加载从 CSV 切换到 SQLite

```python
# 旧: 读取 feedback CSV → 提取特征
# 新: 直接从 SQLite 读取已存储的特征
def _load_training_data(db, session_ids):
    actions = storage.get_training_actions(db, session_ids)
    for a in actions:
        features = a.get("features")  # 40 维特征已在上传时存入 DB
        all_features.append(features)
        all_labels.append(a["manual_quality"])
```

**改动 2**: 增加 Train/Test Split

```python
# 旧: 全量数据训练 + 全量数据评估（过拟合）
# 新: 80/20 分层划分
sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(sss.split(X, y_encoded))

# 在 test set 上评估
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

# 用全量数据重新训练最终模型（用于导出）
model.fit(X, y_encoded)
```

这确保了报告的准确率是真实泛化性能，而非训练集拟合度。

#### Step 5: 更新所有 Router

所有 4 个 router 文件都添加了 `Depends(get_db)` 依赖注入：

```python
# 每个路由函数增加 db 参数
async def list_sessions(db: DBSession = Depends(get_db)):
    sessions = storage.list_sessions(db)
```

**sessions.py 新增端点**：
- `GET /{session_id}/actions` — 获取动作列表
- `POST /{session_id}/actions/delete` — 软删除
- `POST /{session_id}/actions/restore` — 恢复
- `PUT /{session_id}/actions/{action_id}` — 更新标注

**sessions.py 上传逻辑变化**：
原来只存 CSV 文件；现在还会解析 Feedback CSV 的每一行，提取 40 维特征，存入 `actions` 表。

```python
FEATURE_COLS = [
    'mean_accX', 'std_accX', 'max_accX', 'min_accX', 'simpson_accX',
    # ... 共 40 列
]

def _extract_features_from_row(row):
    return [float(row[c]) for c in FEATURE_COLS]
```

#### Step 6: 更新 main.py

```python
from db.database import init_db

@app.on_event("startup")
def on_startup():
    init_db()  # 启动时自动建表
```

版本号从 1.x 升级到 2.0.0。

#### Step 7: 更新 config.py

```python
database_url: str = f"sqlite:///{Path(__file__).parent / 'storage' / 'tennis_coach.db'}"
```

数据库文件放在 `backend/storage/` 目录下，与 CSV 文件同级。

---

## 4. DataPipeline 整合页面

### 4.1 设计动机

原先上传和清洗是两个独立页面（Upload + Clean），用户需要来回切换。整合为一个页面后，工作流变为：

```
Step 1: 上传 CSV → Step 2: 预览/筛选 → Step 3: 查看波形 → Step 4: 训练就绪检查
```

### 4.2 实现细节

**文件**: `frontend/pages/2_📤_DataPipeline.py`

#### Step 1: 上传 CSV

- 两个文件上传区（Raw IMU CSV + Feedback CSV）
- 可选关联到已有项目
- 上传前预览行数和 Good/Bad 统计
- 上传后自动跳到 Step 2

#### Step 2: 预览和筛选

- `st.data_editor` 可编辑表格展示所有动作
- 支持操作：勾选删除、恢复已删除、修改质量标注
- 实时显示统计：总样本、有效样本、Good、Bad、已删除
- 删除/恢复通过 API 调用 soft delete 端点

#### Step 3: 单样本 IMU 波形

- 选择动作序号 → 加载该动作时间窗口的 IMU 数据
- Plotly 图表展示 AccX/Y/Z 和 AccMag 波形
- 调用 `GET /api/viz/action-window/{session_id}/{action_index}` 端点
- 后端从 Raw CSV 中按 `t_start`/`t_end` 时间截取窗口

#### Step 4: 训练就绪检查

- 检查条件：至少 10 个标注样本 + 同时有 Good 和 Bad
- 满足条件显示 "数据就绪" + 引导跳转到 Train 页面
- 不满足显示具体缺失原因

### 4.3 旧页面处理

- `2_📤_Upload.py` → 已删除
- `4_🧹_Clean.py` → 已删除
- `5_🤖_Train.py` → 重命名为 `4_🤖_Train.py`

---

## 5. API 端点详解

### Sessions

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/sessions/upload` | 上传 CSV 文件（multipart/form-data） |
| GET | `/api/sessions/list` | 列出所有 session |
| GET | `/api/sessions/{id}` | 获取单个 session |
| DELETE | `/api/sessions/{id}` | 删除 session（含 CSV 文件） |
| GET | `/api/sessions/{id}/actions` | 获取动作列表，`?include_deleted=true` |
| POST | `/api/sessions/{id}/actions/delete` | 软删除动作，body: `[action_id, ...]` |
| POST | `/api/sessions/{id}/actions/restore` | 恢复动作，body: `[action_id, ...]` |
| PUT | `/api/sessions/{id}/actions/{aid}` | 更新标注，body: `{"manual_quality": "good"}` |

### Projects

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/projects/list` | 列出项目 |
| POST | `/api/projects/create` | 创建项目 |
| GET | `/api/projects/{id}` | 获取项目详情（含 sessions） |
| DELETE | `/api/projects/{id}` | 删除项目 |

### Training

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/training/start` | 开始训练 |
| GET | `/api/training/runs` | 列出训练历史 |
| GET | `/api/training/status/{id}` | 获取训练状态 |
| GET | `/api/training/download/{id}` | 下载模型，`?fmt=auto/mlmodel/pkl` |

### Visualization

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/viz/raw-data/{id}` | 获取 Raw IMU 数据，`?sample_rate=2000` |
| GET | `/api/viz/feedback-data/{id}` | 获取动作质量数据 |
| GET | `/api/viz/action-window/{id}/{idx}` | 获取单动作 IMU 窗口 |

---

## 6. 构建与运行

### 环境搭建

```bash
# 创建 Conda 环境
conda env create -f environment.yml
conda activate tennis-web

# 安装额外依赖（如果 conda 环境不完整）
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 启动服务

```bash
# 方式 1: 一键启动
./start.sh

# 方式 2: 分别启动
# 终端 1 - Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 终端 2 - Frontend
cd frontend
streamlit run app.py --server.headless true
```

### 后台运行（不随终端关闭）

```bash
cd backend && nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/tennis_backend.log 2>&1 &
cd frontend && nohup streamlit run app.py --server.headless true > /tmp/tennis_frontend.log 2>&1 &
```

### 生成测试数据

```bash
cd backend
python generate_test_data.py
# 输出到 ../data/ 目录，然后在 DataPipeline 页面上传
```

### 端口

| 服务 | 端口 | URL |
|------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Frontend UI | 8501 | http://localhost:8501 |
| API 文档 | 8000 | http://localhost:8000/docs |

---

## 7. 测试记录

### 7.1 数据库初始化测试

```bash
cd backend
python -c "
from db.database import init_db, engine
from sqlalchemy import inspect

init_db()
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Tables: {tables}')
"
```

**结果**: `Tables: ['actions', 'projects', 'sessions', 'training_runs']` — 4 张表全部创建成功。

### 7.2 API 端点测试

#### 健康检查
```bash
curl http://localhost:8000/health
# {"status":"healthy"}
```

#### 上传 CSV
```bash
curl -X POST http://localhost:8000/api/sessions/upload \
  -F "raw_csv=@data/test_raw.csv" \
  -F "feedback_csv=@data/test_feedback.csv" \
  -F "session_name=test_forehand"
```
**结果**:
```json
{
    "status": "success",
    "id": "438a0357-...",
    "name": "test_forehand",
    "action_count": 25,
    "good_count": 11,
    "bad_count": 14,
    "unlabeled_count": 0
}
```

#### Session 列表
```bash
curl http://localhost:8000/api/sessions/list
```
**结果**: 返回 1 个 session，字段完整。

#### 动作列表（含 40 维特征）
```bash
curl http://localhost:8000/api/sessions/{id}/actions
```
**结果**: 返回 25 个 action，每个都有 40 维 `features` 数组。

#### 软删除 + 恢复
```bash
# 删除
curl -X POST "http://localhost:8000/api/sessions/{id}/actions/delete" \
  -H "Content-Type: application/json" -d "[1, 2]"
# → action_count: 25 → 23, good_count: 11 → 10

# 恢复
curl -X POST "http://localhost:8000/api/sessions/{id}/actions/restore" \
  -H "Content-Type: application/json" -d "[1, 2]"
# → action_count: 23 → 25, good_count: 10 → 11
```

**结果**: 软删除和恢复均正常工作，session 的计数自动更新。

#### 模型训练
```bash
curl -X POST http://localhost:8000/api/training/start \
  -H "Content-Type: application/json" \
  -d '{"session_ids": ["438a0357-..."], "model_type": "svm"}'
```
**结果**:
```json
{
    "run_id": "0640d75f",
    "status": "completed",
    "accuracy": 0.8,
    "precision": 0.867,
    "recall": 0.8,
    "f1_score": 0.8,
    "cv_mean": 0.88,
    "cv_std": 0.16,
    "confusion_matrix": [[2,1],[0,2]],
    "labels": ["bad","good"],
    "coreml_exported": false
}
```

80% 测试集准确率，5 折交叉验证 88%±16%。

#### 模型下载
```bash
curl -o model.pkl "http://localhost:8000/api/training/download/0640d75f?fmt=pkl"
# HTTP 200, 文件大小 7552 bytes
```

#### 可视化端点
```bash
# Raw IMU 数据（降采样到 100 点）
curl "http://localhost:8000/api/viz/raw-data/{id}?sample_rate=100"
# → 100 rows, columns: [time, userAccelX, userAccelY, userAccelZ, ...]

# 动作窗口
curl "http://localhost:8000/api/viz/action-window/{id}/3"
# → 返回第 3 个动作的 IMU 窗口数据 + action 元信息
```

### 7.3 SQLite 数据验证

```bash
python -c "
import sqlite3
db = sqlite3.connect('storage/tennis_coach.db')
for table in ['projects', 'sessions', 'training_runs', 'actions']:
    count = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'{table}: {count} rows')
"
```

**结果**:
```
projects: 1 rows
sessions: 1 rows
training_runs: 1 rows
actions: 25 rows
```

---

## 8. Debug 记录

### Bug 1: Pydantic protected namespace 警告

**现象**: 启动时 Pydantic 报警告：
```
Field "model_type" has conflict with protected namespace "model_"
```

**原因**: Pydantic v2 默认将 `model_` 前缀视为保护命名空间。`TrainingRequest` 中的 `model_type` 字段触发了这个限制。

**修复**: 在 `TrainingRequest` 类中添加配置禁用保护命名空间：
```python
class TrainingRequest(BaseModel):
    model_config = {"protected_namespaces": ()}  # 添加这行
    model_type: str = "svm"
    # ...
```

**文件**: `backend/routers/training.py`

---

### Bug 2: 模型下载 404

**现象**: `GET /api/training/download/{run_id}` 返回 404。

**原因**: 下载端点只查找 `.mlmodel` 文件，但 CoreML 导出依赖 `coremltools` 库。如果该库未安装（常见于非 macOS 环境），只会生成 `.pkl` 文件。

**修复**: 下载端点增加 `fmt` 参数，支持三种模式：
```python
@router.get("/download/{run_id}")
async def download_model(run_id: str, fmt: str = "auto"):
    if fmt == "auto":
        exts = [".mlmodel", ".pkl"]  # 优先 mlmodel，其次 pkl
    elif fmt == "pkl":
        exts = [".pkl"]
    # ...
```

同时在 Train 前端页面增加 pkl 下载链接：
```python
with col2:
    st.markdown(f"**下载 Pickle 模型**")
    st.markdown(f"[点击下载]({API_URL}/api/training/download/{run_id}?fmt=pkl)")
```

**文件**: `backend/routers/training.py`, `frontend/pages/4_🤖_Train.py`

---

### Bug 3: st.page_link 不存在

**现象**: DataPipeline 页面报错 `AttributeError: module 'streamlit' has no attribute 'page_link'`

**原因**: `st.page_link()` 在 Streamlit 1.31.0 才引入，当前环境是 1.30.0。

**修复**: 将 `st.page_link()` 替换为 `st.markdown()` 文本提示：
```python
# 旧:
st.page_link("pages/5_🤖_Train.py", label="前往模型训练", icon="🤖")

# 新:
st.markdown("👉 请在左侧导航栏点击 **🤖 Train** 页面开始训练")
```

**文件**: `frontend/pages/2_📤_DataPipeline.py`

---

### Bug 4: 峰值标记坐标不匹配

**现象**: Visualize 页面的峰值标记（vline）位置不正确——标记显示在图表外。

**原因**:
- 图表 x 轴使用 `seconds_elapsed`（0~60 秒）
- 但 `t_peak` 是 Unix 时间戳（如 `1708180002.37`）
- 两者差了一个 `base_time` 偏移量

**修复**: 从 Raw 数据获取第一行的 `time` 值作为基准，将 `t_peak` 转换为相对时间：
```python
raw_for_peaks = api_get(f"/api/viz/raw-data/{sid}?sample_rate=1")
first_row = raw_for_peaks["data"][0]
base_time = float(first_row.get("time", 0))

for action in fb["actions"]:
    x_val = action["t_peak"] - base_time  # Unix timestamp → seconds_elapsed
    fig.add_vline(x=x_val, ...)
```

**文件**: `frontend/pages/3_📈_Visualize.py`

---

### Bug 5: 服务进程自动退出

**现象**: 通过 Claude Code 的 `run_in_background` 启动的 uvicorn 和 streamlit 进程在后台任务完成后自动退出。

**原因**: Claude Code 的后台任务模式会在 shell 命令执行完毕后关闭进程组。

**修复**: 使用 `nohup` 启动服务，确保进程不受终端生命周期影响：
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/tennis_backend.log 2>&1 &
nohup streamlit run app.py --server.headless true > /tmp/tennis_frontend.log 2>&1 &
```

---

### Bug 6: Train 页面路径过时

**现象**: DataPipeline 页面引用 `pages/5_🤖_Train.py`，但 Train 页面已重命名为 `4_🤖_Train.py`。

**修复**: 与 Bug 3 一同修复 — 直接改为文本提示，不再硬编码文件路径。

---

## 9. 后续规划：LLM Agent 接入

### 为什么 SQLite 迁移对 Agent 至关重要

未来计划使用 LangGraph 构建 LLM Agent，定义 6 个工具：

| Agent Tool | 对应 SQL 查询 |
|-----------|-------------|
| `query_session_stats` | `SELECT good_count, bad_count FROM sessions WHERE ...` |
| `compare_models` | `SELECT accuracy, f1_score FROM training_runs ORDER BY ...` |
| `get_data_distribution` | `SELECT manual_quality, COUNT(*) FROM actions GROUP BY ...` |
| `suggest_training_config` | 基于历史 `training_runs` 的 hyperparameters + accuracy |
| `trigger_training` | 调用现有 `/api/training/start` 端点 |
| `analyze_action_patterns` | `SELECT features FROM actions WHERE manual_quality = ...` |

如果仍然使用 JSON 文件存储，每个 tool 都需要遍历文件目录、读取解析 JSON，实现复杂且低效。SQLite 使这些查询变成简单的 SQL 语句。

### RAG 策略

- **结构化数据**（训练数据统计、模型性能）→ 直接 SQL 查询，不需要向量搜索
- **领域知识**（网球技术文档、教学视频描述）→ 向量数据库（如 ChromaDB），规模很小（<100 条），embedding 后检索

这种混合策略避免了"把所有东西都塞进向量数据库"的常见错误。

---

## 附录

### 40 维特征说明

来自 iOS App 的 Feedback CSV，每个动作一行：

| 特征组 | 通道 | 统计量 | 维度 |
|--------|------|--------|------|
| 加速度 | AccX, AccY, AccZ, AccMag | mean, std, max, min, simpson | 4 × 5 = 20 |
| 陀螺仪 | GyroX, GyroY, GyroZ, GyroMag | mean, std, max, min, simpson | 4 × 5 = 20 |

注意：App 端使用 `mean/std/max/min/simpson` 5 个统计量；Web 端 `feature_extractor.py` 使用 `mean/std/max/rms/zcr` 5 个统计量。两者不完全一致，训练时使用的是 App 端导出的特征。

### Git 版本管理

```bash
# 初始化
git init
git remote add origin https://github.com/jiayingtu21-hash/CoachWeb.git

# 初次提交
git add .gitignore WORKFLOW.md environment.yml start.sh backend/ frontend/
git commit -m "feat: SQLite migration + integrated DataPipeline page"
git push -u origin main
```

`.gitignore` 排除：
- `backend/storage/` 下的运行时数据（数据库、CSV、模型）
- `data/` 测试数据目录
- Python 缓存、IDE 配置、OS 文件
- `.env` 环境变量文件
- `.claude/` Claude Code 本地配置
