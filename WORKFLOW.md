# Tennis Coach Web MVP - 完整构建流程

> **构建时间**: 2026-02-17
> **技术栈**: Streamlit (前端) + FastAPI (后端) + 本地 JSON 文件存储
> **目标**: 从零搭建一个可运行的 MVP，能上传 CSV、可视化数据、清洗数据、训练模型

---

## 目录

1. [项目背景与架构设计](#1-项目背景与架构设计)
2. [Step 1: 检查现有项目骨架](#2-step-1-检查现有项目骨架)
3. [Step 2: 分析 iOS App 的 CSV 导出格式](#3-step-2-分析-ios-app-的-csv-导出格式)
4. [Step 3: 检查本地开发环境](#4-step-3-检查本地开发环境)
5. [Step 4: 创建 Conda 环境配置](#5-step-4-创建-conda-环境配置)
6. [Step 5: 重写后端配置 - 去掉 Supabase 依赖](#6-step-5-重写后端配置---去掉-supabase-依赖)
7. [Step 6: 创建本地文件存储服务](#7-step-6-创建本地文件存储服务)
8. [Step 7: 重写所有 API 路由](#8-step-7-重写所有-api-路由)
9. [Step 8: 创建模型训练服务](#9-step-8-创建模型训练服务)
10. [Step 9: 重写 FastAPI 主入口](#10-step-9-重写-fastapi-主入口)
11. [Step 10: 精简依赖文件](#11-step-10-精简依赖文件)
12. [Step 11: 构建 Streamlit 前端（6 个页面）](#12-step-11-构建-streamlit-前端6-个页面)
13. [Step 12: 创建测试数据生成器](#13-step-12-创建测试数据生成器)
14. [Step 13: 创建一键启动脚本](#14-step-13-创建一键启动脚本)
15. [Step 14: 安装环境并测试](#15-step-14-安装环境并测试)
16. [最终项目结构](#16-最终项目结构)
17. [日常启动方法](#17-日常启动方法)

---

## 1. 项目背景与架构设计

### 要解决的问题

Tennis Coach iOS App 可以录制网球动作的 IMU 传感器数据（加速度、陀螺仪），并导出两种 CSV：
- **Raw CSV**: 100Hz 的传感器原始数据流（每秒 100 行）
- **Feedback CSV**: 每个动作的汇总（峰值时间、质量标注、40 维特征向量）

我们需要一个 Web 端来：上传这些 CSV → 可视化数据 → 清洗不良数据 → 训练 ML 模型 → 导出 CoreML 模型回 App 使用。

### 架构设计思路

```
┌──────────────────────┐         HTTP          ┌──────────────────────┐
│   Streamlit 前端      │ ◄──── 请求/响应 ────► │   FastAPI 后端        │
│   (localhost:8501)    │                       │   (localhost:8000)    │
│                       │                       │                       │
│   - Dashboard         │                       │   - CSV 解析          │
│   - 项目管理          │                       │   - 特征提取          │
│   - CSV 上传          │                       │   - 峰值检测          │
│   - 数据可视化        │                       │   - 模型训练          │
│   - 数据清洗          │                       │   - CoreML 导出       │
│   - 模型训练          │                       │                       │
└──────────────────────┘                       └──────────┬───────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────────┐
                                               │   本地文件存储        │
                                               │   backend/storage/    │
                                               │                       │
                                               │   - projects/*.json   │
                                               │   - sessions/*.json   │
                                               │   - csv_files/*/      │
                                               │   - models/*.pkl      │
                                               │   - training_runs/    │
                                               └──────────────────────┘
```

### 关键简化决策

原始规划中使用 Supabase（PostgreSQL + Storage），但 MVP 阶段改为 **本地 JSON + CSV 文件存储**：
- 不需要注册任何外部服务
- 不需要配置数据库连接
- 今天就能跑起来
- 数据结构完全一样，后期可以直接替换为 Supabase

---

## 2. Step 1: 检查现有项目骨架

### 目的
了解项目里已经有哪些文件，哪些是空壳需要填充，哪些需要重写。

### 执行的命令

```bash
# 查看目录结构
ls -la /Users/mymini/Desktop/tennis_coach_JT/coachWeb/tennis-coach-web/

# 查看所有文件
# 使用 Glob 工具匹配 **/* 模式
```

### 发现的现有文件

```
backend/
├── main.py                 # ✅ 有内容，FastAPI 骨架
├── config.py               # ⚠️ 有 Supabase/Redis 配置，需要简化
├── .env.example            # ✅ 环境变量模板
├── requirements.txt        # ⚠️ 依赖太多（含 Supabase/Redis/Celery）
├── routers/
│   ├── __init__.py         # ✅ 空文件
│   ├── sessions.py         # ⚠️ 有骨架，TODO 很多，返回 Mock 数据
│   ├── projects.py         # ⚠️ 同上
│   ├── training.py         # ⚠️ 同上
│   └── visualization.py    # ⚠️ 同上
├── services/
│   ├── csv_parser.py       # ✅ 已实现，CSV 解析 + 峰值检测
│   └── feature_extractor.py # ✅ 已实现，40 维特征提取
frontend/
├── requirements.txt        # ✅ Streamlit 依赖
├── .streamlit/config.toml  # ✅ 主题配置
data/                       # 空目录
```

### 结论
- `csv_parser.py` 和 `feature_extractor.py` 已经写好，可以直接用
- 所有 router 返回的是 Mock 数据，需要接入真实存储
- 缺少：存储层、模型训练服务、整个前端
- `config.py` 依赖 Supabase/Redis，需要简化

---

## 3. Step 2: 分析 iOS App 的 CSV 导出格式

### 目的
确认 App 实际导出的 CSV 格式，确保后端解析逻辑正确。

### 方法
扫描 `/Users/mymini/Desktop/tennis_coach_JT/coachApp/` 下的 Swift 源码，找到 CSV 导出逻辑。

### 发现的 CSV 格式

#### Raw CSV（20 列）
来自 `SessionCSVLogger.swift`，100Hz IMU 数据流：

```
session_id, session_type, seconds_elapsed, time,
accelerationX, accelerationY, accelerationZ,
userAccelX, userAccelY, userAccelZ,
gravityX, gravityY, gravityZ,
rotationRateX, rotationRateY, rotationRateZ,
quaternionW, quaternionX, quaternionY, quaternionZ
```

#### Feedback CSV（51 列）
来自 `FeedbackCSVExporter.swift`，每个动作一行：

```
session_id, action_index, t_peak, t_start, t_end,
ml_classification, ml_quality, manual_quality,
[40 维特征: mean/std/max/min/simpson × 8 通道],
isoTime
```

40 维特征的 8 个通道: `accX, accY, accZ, accMag, gyroX, gyroY, gyroZ, gyroMag`
每个通道 5 个统计量: `mean, std, max, min, simpson`（Simpson 积分）

### 这一步的意义
- 确认了 Feedback CSV **自带 40 维特征**，不需要后端重新从 Raw CSV 提取
- 发现特征用的是 `min` 和 `simpson`，而不是原来 `feature_extractor.py` 里的 `rms` 和 `zcr`
- 模型训练可以直接读 Feedback CSV 的特征列

---

## 4. Step 3: 检查本地开发环境

### 执行的命令

```bash
which conda        # → /Users/mymini/miniconda3/bin/conda ✅
which python3      # → /Users/mymini/miniconda3/bin/python3
python3 --version  # → Python 3.13.11（系统 Python，不是我们要用的）
```

### 结论
- Miniconda 已安装（通过 Homebrew）
- 需要创建独立的 Conda 环境，用 Python 3.11（兼容性更好）

---

## 5. Step 4: 创建 Conda 环境配置

### 创建的文件: `environment.yml`

**位置**: 项目根目录 `tennis-coach-web/environment.yml`

**作用**: 定义 Conda 环境，一键创建所有依赖。把科学计算库（numpy/pandas/sklearn）通过 conda 安装（预编译二进制，更稳定），其余通过 pip 安装。

**内容要点**:
- Python 3.11
- conda 安装: numpy, pandas, scikit-learn
- pip 安装: fastapi, uvicorn, streamlit, plotly, coremltools, httpx, pydantic 等

---

## 6. Step 5: 重写后端配置 - 去掉 Supabase 依赖

### 修改的文件: `backend/config.py`

**改动前**: 包含 `supabase_url`, `supabase_key`, `database_url`, `redis_url`, `anthropic_api_key` 等配置

**改动后**: 只保留两个配置项：
- `debug: bool = True`
- `data_dir: str` → 指向 `backend/storage/` 目录

**设计思路**: MVP 不需要任何外部服务。数据全部存在本地 `backend/storage/` 目录下。这个目录会自动创建。后期要接 Supabase 时，只需要把 `storage.py` 里的读写函数换成 Supabase API 调用。

---

## 7. Step 6: 创建本地文件存储服务

### 创建的文件: `backend/services/storage.py`

**作用**: 替代 Supabase，用本地文件系统实现所有 CRUD 操作。

**存储结构**:
```
backend/storage/
├── projects/           # 每个项目一个 JSON 文件
│   └── {project_id}.json
├── sessions/           # 每个 session 一个 JSON 文件（元数据）
│   └── {session_id}.json
├── csv_files/          # 每个 session 的 CSV 文件
│   └── {session_id}/
│       ├── raw.csv
│       └── feedback.csv
├── models/             # 训练好的模型文件
│   └── {run_id}.pkl
└── training_runs/      # 训练记录
    └── {run_id}.json
```

**提供的函数** (按模块分):

| 模块 | 函数 | 作用 |
|------|------|------|
| Projects | `list_projects()` | 列出所有项目 |
| | `get_project(id)` | 获取项目详情 |
| | `create_project(id, name, desc)` | 创建项目 |
| | `delete_project(id)` | 删除项目 |
| | `add_session_to_project(pid, sid)` | 关联 session 到项目 |
| Sessions | `list_sessions(project_id?)` | 列出 sessions（可按项目筛选） |
| | `get_session(id)` | 获取 session 详情 |
| | `save_session(id, data)` | 保存 session 元数据 |
| | `delete_session(id)` | 删除 session + 关联 CSV |
| CSV | `save_csv(sid, filename, content)` | 保存 CSV 内容 |
| | `load_csv(sid, filename)` | 读取 CSV 内容 |
| Training | `save_training_run(rid, data)` | 保存训练记录 |
| | `get_training_run(rid)` | 获取训练记录 |
| | `list_training_runs()` | 列出所有训练记录 |
| Models | `get_model_path(rid, ext)` | 获取模型文件路径 |

### 同时创建: `backend/services/__init__.py`
空文件，让 `services` 成为 Python 包。

---

## 8. Step 7: 重写所有 API 路由

### 修改的文件: `backend/routers/sessions.py`

**改动**: 从返回 Mock 数据 → 接入 `storage.py` 真实读写

**API 端点**:
| 方法 | 路径 | 作用 |
|------|------|------|
| POST | `/api/sessions/upload` | 上传 Raw + Feedback 两个 CSV |
| GET | `/api/sessions/list` | 列出所有 session |
| GET | `/api/sessions/{id}` | 获取 session 详情 |
| DELETE | `/api/sessions/{id}` | 删除 session |

**上传流程**:
1. 接收两个 CSV 文件 (multipart form)
2. 用 `csv_parser.py` 解析并验证格式
3. 统计 good/bad/unlabeled 数量
4. 保存 CSV 到 `storage/csv_files/{session_id}/`
5. 保存元数据 JSON 到 `storage/sessions/`
6. 如果指定了 project_id，关联到项目

---

### 修改的文件: `backend/routers/projects.py`

**API 端点**:
| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/projects/list` | 列出所有项目（含 session 数量） |
| POST | `/api/projects/create` | 创建项目（JSON body: name, description） |
| GET | `/api/projects/{id}` | 获取项目详情（含关联的 sessions） |
| DELETE | `/api/projects/{id}` | 删除项目 |

---

### 修改的文件: `backend/routers/visualization.py`

**API 端点**:
| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/viz/raw-data/{session_id}` | 获取 IMU 数据（支持降采样） |
| GET | `/api/viz/feedback-data/{session_id}` | 获取动作列表 |

**raw-data 端点的设计**:
- 从 storage 读取 raw.csv → pandas DataFrame
- 支持 `sample_rate` 参数做降采样（大文件优化）
- 自动计算 `accMag`（加速度 magnitude）
- 只返回前端需要的列（减少传输量）

**feedback-data 端点的设计**:
- 只返回 `action_index, t_peak, t_start, t_end, ml_classification, ml_quality, manual_quality`
- 不返回 40 维特征（前端不需要，减少传输）

---

### 修改的文件: `backend/routers/training.py`

**API 端点**:
| 方法 | 路径 | 作用 |
|------|------|------|
| POST | `/api/training/start` | 启动训练（JSON body 指定 sessions + 超参数） |
| GET | `/api/training/runs` | 列出训练历史 |
| GET | `/api/training/status/{run_id}` | 查询单次训练状态 |
| GET | `/api/training/download/{run_id}` | 下载 CoreML 模型文件 |

**训练请求参数** (Pydantic Model):
- `session_ids`: 选中的 session 列表
- `model_type`: "svm" / "decision_tree" / "random_forest"
- `svm_c`, `svm_kernel`: SVM 超参数
- `max_depth`, `n_estimators`: 树模型超参数

---

## 9. Step 8: 创建模型训练服务

### 创建的文件: `backend/services/model_trainer.py`

**作用**: 核心 ML 训练逻辑，从 Feedback CSV 读取特征 → 训练 sklearn 模型 → 导出。

**训练流程**:
1. **加载数据**: 遍历选中的 session_ids，读取每个 feedback.csv
2. **筛选标注**: 过滤掉 `manual_quality == "unlabeled"` 的样本
3. **提取特征**: 读取 CSV 中的 40 维特征列（`mean_accX`, `std_accX`, ...）
4. **创建模型**: 根据 `model_type` 创建 SVM / 决策树 / 随机森林
5. **交叉验证**: 5-fold CV 评估泛化能力
6. **全量训练**: 用全部数据训练最终模型
7. **评估指标**: accuracy, precision, recall, F1, 混淆矩阵
8. **保存模型**: pickle 格式保存到 `storage/models/`
9. **CoreML 导出**: 尝试用 coremltools 转换（可选）
10. **保存记录**: 训练结果 JSON 保存到 `storage/training_runs/`

**关键设计决策**:
- 直接从 Feedback CSV 读取 40 维特征，而不是从 Raw CSV 重新提取
  - 因为 App 导出时已经计算好了特征，保证了一致性
- NaN 处理: `np.nan_to_num(X, nan=0.0)` 避免训练崩溃
- CoreML 导出是 try/except 的，失败不影响训练本身

---

## 10. Step 9: 重写 FastAPI 主入口

### 修改的文件: `backend/main.py`

**改动**: 精简代码，去掉 debug 模式判断（MVP 阶段 docs 始终开启）

**做的事情**:
1. 创建 FastAPI 应用
2. 配置 CORS（允许 Streamlit 端口 8501 访问）
3. 注册 4 个路由模块: sessions, projects, training, visualization
4. 提供健康检查端点 `/` 和 `/health`

---

## 11. Step 10: 精简依赖文件

### 修改的文件: `backend/requirements.txt`

**改动前** (15 个包，含 supabase, asyncpg, sqlalchemy, celery, redis, anthropic, pytest):
```
fastapi, uvicorn, python-multipart,
pandas, numpy, scikit-learn, coremltools,
sqlalchemy, asyncpg, supabase,
python-dotenv, pydantic, pydantic-settings,
celery, redis, anthropic,
pytest, pytest-asyncio, pytest-cov, httpx
```

**改动后** (9 个包，MVP 最小依赖):
```
fastapi, uvicorn, python-multipart,
pandas, numpy, scikit-learn,
python-dotenv, pydantic, pydantic-settings
```

**去掉的原因**:
- `supabase, sqlalchemy, asyncpg`: 改用本地文件存储
- `celery, redis`: MVP 不需要异步任务队列
- `anthropic`: Phase 2 才需要 LLM
- `pytest` 等: 开发依赖，不影响运行
- `coremltools`: 通过 conda/pip 单独装（可选）

---

## 12. Step 11: 构建 Streamlit 前端（6 个页面）

### 创建目录

```bash
mkdir -p frontend/pages
```

### 页面 0: `frontend/app.py` - Dashboard 主页

**作用**: 首页，显示项目和 Session 的总览

**功能**:
- 检查后端连接（请求 `/health`），未连接则显示错误提示
- 左列: 项目列表（名称 + session 数量）
- 右列: Session 列表（名称 + good/bad 统计）
- 底部: 总计指标卡片（总 Sessions、总动作、Good、Bad）

---

### 页面 1: `frontend/pages/1_📊_Projects.py` - 项目管理

**作用**: 创建和管理训练项目（一个项目包含多个 session）

**功能**:
- 创建项目表单（名称 + 描述）
- 项目列表卡片（每个项目显示名称、ID、session 数量、删除按钮）
- 展开可查看关联的 sessions

---

### 页面 2: `frontend/pages/2_📤_Upload.py` - CSV 上传

**作用**: 上传从 App 导出的两个 CSV 文件

**功能**:
- 项目选择下拉框（可选关联到某个项目）
- Session 名称输入（可选）
- 双列布局: 左边上传 Raw CSV，右边上传 Feedback CSV
- 上传后实时预览: 显示行数、列数、前 10 行数据
- "上传到服务器"按钮: 发送 multipart form 到后端 `/api/sessions/upload`

---

### 页面 3: `frontend/pages/3_📈_Visualize.py` - 数据可视化

**作用**: 可视化 IMU 传感器数据和动作质量分布

**功能**:
- Session 多选框（可选多个 session 叠加对比）
- 显示轴选择: AccX, AccY, AccZ, AccMag, GyroX, GyroY, GyroZ
- 降采样滑块（0-5000 点，避免大文件卡顿）
- **IMU 时序图** (Plotly): 加速度/陀螺仪随时间变化曲线
  - 多 session 用不同颜色
  - 支持缩放、平移、hover 交互
- **动作质量散点图** (Plotly): 每个动作的质量标注
  - 绿色 = Good, 红色 = Bad, 灰色 = Unlabeled
  - 悬停显示峰值时间
- 统计指标卡片: Good / Bad / Unlabeled 数量

---

### 页面 4: `frontend/pages/4_🧹_Clean.py` - 数据清洗

**作用**: 查看和修改动作标注

**功能**:
- Session 选择下拉框
- 统计卡片: 总计、Good、Bad、Unlabeled
- **可编辑数据表格** (`st.data_editor`):
  - `manual_quality` 列可以用下拉框修改（good/bad/unlabeled）
  - 其余列只读
- 筛选工具:
  - 按质量筛选（多选: good/bad/unlabeled）
  - 按时间范围筛选（滑块）

---

### 页面 5: `frontend/pages/5_🤖_Train.py` - 模型训练

**作用**: 选择数据和超参数 → 训练模型 → 查看结果 → 下载

**功能**:
- **Step 1**: Session 多选框（显示每个 session 的 Good/Bad 数量）
- **Step 2**: 模型配置
  - 模型类型: SVM / 决策树 / 随机森林
  - 超参数滑块（C、kernel、max_depth、n_estimators）
- **Step 3**: "开始训练"按钮 + 加载动画
- **Step 4**: 训练结果展示
  - 指标卡片: 准确率、精确率、召回率、F1
  - 交叉验证分数
  - 混淆矩阵热力图 (Plotly)
  - CoreML 模型下载链接
- **训练历史**: 底部列出所有历史训练记录

---

### Streamlit 配置: `frontend/.streamlit/config.toml`

**已存在，未修改**。定义了主题颜色：
- 主色: `#FF6B35`（橙色）
- 背景: 白色
- 字体: sans serif

---

## 13. Step 12: 创建测试数据生成器

### 创建的文件: `backend/generate_test_data.py`

**作用**: 生成模拟的 Raw CSV 和 Feedback CSV，用于测试所有功能

**运行方式**:
```bash
cd backend
python generate_test_data.py
```

**生成逻辑**:
1. 创建 60 秒、100Hz 的模拟 IMU 数据（6000 行）
2. 在随机时间点注入 25 个动作峰值
   - 65% 概率为 "good"（高加速度、平滑钟形曲线）
   - 35% 概率为 "bad"（低加速度、不规则噪声）
3. 为每个动作计算 40 维特征（mean/std/max/min/simpson × 8 通道）
4. 输出两个 CSV 到 `data/` 目录

**输出文件**:
- `data/{session_id}_create_test.csv` - Raw IMU (6000 行, 20 列)
- `data/{session_id}_feedback_test.csv` - Feedback (25 行, 51 列)

---

## 14. Step 13: 创建一键启动脚本

### 创建的文件: `start.sh`

**作用**: 一个脚本同时启动后端和前端

**逻辑**:
1. 检查 conda 是否安装
2. 如果 `tennis-web` 环境不存在，自动创建并安装所有依赖
3. 激活环境
4. 后台启动后端: `uvicorn main:app --reload --port 8000`
5. 后台启动前端: `streamlit run app.py --server.port 8501`
6. 显示访问地址
7. Ctrl+C 同时停止两个服务

**使用方式**:
```bash
chmod +x start.sh
bash start.sh
```

---

## 15. Step 14: 安装环境并测试

### 15.1 创建 Conda 环境

```bash
# 加载 conda
source /Users/mymini/miniconda3/etc/profile.d/conda.sh

# 创建 Python 3.11 环境
conda create -n tennis-web python=3.11 -y

# 激活
conda activate tennis-web

# 安装科学计算库（conda 预编译版本）
conda install numpy pandas scikit-learn -y

# 安装其余依赖（pip）
pip install fastapi==0.109.0 "uvicorn[standard]==0.27.0" python-multipart==0.0.6 \
    streamlit==1.30.0 plotly==5.18.0 httpx==0.26.0 python-dotenv==1.0.0 \
    pydantic==2.5.3 pydantic-settings==2.1.0 requests==2.31.0
```

### 15.2 测试后端导入

```bash
cd backend

# 测试所有模块能否正确导入
python -c "
from main import app
from services.csv_parser import parse_raw_csv, parse_feedback_csv, validate_csv_format
from services.feature_extractor import extract_features, get_feature_names
from services import storage
from services.model_trainer import run_training
print('All imports OK')
"
# 输出: All imports OK ✅
```

### 15.3 启动后端并测试 API

```bash
# 启动后端
uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 3

# 测试健康检查
curl -s http://localhost:8000/
# 输出: {"message":"Tennis Coach API","version":"1.0.0","status":"running"} ✅
```

### 15.4 生成测试数据

```bash
python generate_test_data.py
# 输出:
# Session ID: 3403089b-ee50-4c78-a2ff-80a89bf87697
# Raw CSV: .../data/..._create_test.csv (6000 rows)
# Feedback CSV: .../data/..._feedback_test.csv (25 rows)
# 统计: 25 动作, Good: 11, Bad: 14 ✅
```

### 15.5 测试创建项目 API

```bash
curl -s -X POST http://localhost:8000/api/projects/create \
  -H "Content-Type: application/json" \
  -d '{"name": "正手训练", "description": "正手练习测试"}'

# 输出: {"status":"success","project":{"id":"45e17001","name":"正手训练",...}} ✅
```

### 15.6 测试上传 CSV API

```bash
curl -s -X POST http://localhost:8000/api/sessions/upload \
  -F "raw_csv=@../data/3403089b..._create_test.csv" \
  -F "feedback_csv=@../data/3403089b..._feedback_test.csv" \
  -F "project_id=45e17001" \
  -F "session_name=测试正手 Session 1"

# 输出:
# {
#   "status": "success",
#   "id": "3403089b-ee50-4c78-a2ff-80a89bf87697",
#   "action_count": 25,
#   "good_count": 11,
#   "bad_count": 14
# } ✅
```

### 15.7 测试可视化数据 API

```bash
# Raw IMU 数据（降采样到 100 点）
curl -s "http://localhost:8000/api/viz/raw-data/{session_id}?sample_rate=100"
# 输出: {"session_id":"...","total_rows":100,"data":[{...}]} ✅

# Feedback 数据
curl -s "http://localhost:8000/api/viz/feedback-data/{session_id}"
# 输出: {"session_id":"...","total_actions":25,"actions":[{...}]} ✅
```

### 15.8 测试模型训练 API

```bash
curl -s -X POST http://localhost:8000/api/training/start \
  -H "Content-Type: application/json" \
  -d '{"session_ids": ["3403089b-ee50-4c78-a2ff-80a89bf87697"], "model_type": "svm"}'

# 输出:
# {
#   "run_id": "23979e1a",
#   "status": "completed",
#   "accuracy": 0.92,
#   "precision": 0.92,
#   "recall": 0.92,
#   "f1_score": 0.92,
#   "cv_mean": 0.88,
#   "sample_count": 25,
#   "confusion_matrix": [[13,1],[1,10]]
# } ✅ (92% 准确率!)
```

### 15.9 配置 Streamlit 免交互

```bash
# 跳过 Streamlit 首次运行的邮箱询问
mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml << 'EOF'
[general]
email = ""
EOF
```

### 15.10 启动前端

```bash
cd ../frontend
streamlit run app.py --server.port 8501 --server.headless true

# 输出:
# You can now view your Streamlit app in your browser.
# Network URL: http://192.168.1.151:8501 ✅
```

### 15.11 最终验证

```bash
# 后端健康
curl -s http://localhost:8000/health
# {"status":"healthy"} ✅

# 前端健康
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/_stcore/health
# 200 ✅

# 所有数据可访问
curl -s http://localhost:8000/api/sessions/list    # 1 session ✅
curl -s http://localhost:8000/api/projects/list     # 1 project ✅
curl -s http://localhost:8000/api/training/runs     # 1 training run ✅
```

---

## 16. 最终项目结构

```
tennis-coach-web/
│
├── environment.yml              # Conda 环境定义
├── start.sh                     # 一键启动脚本
│
├── backend/                     # FastAPI 后端
│   ├── main.py                  # 入口: 创建 app, 注册路由, CORS
│   ├── config.py                # 配置: data_dir, debug, allowed_origins
│   ├── requirements.txt         # Python 依赖 (9 个包)
│   ├── .env.example             # 环境变量模板
│   ├── generate_test_data.py    # 测试数据生成器
│   │
│   ├── routers/                 # API 路由层
│   │   ├── __init__.py
│   │   ├── sessions.py          # /api/sessions/* (上传/列表/删除)
│   │   ├── projects.py          # /api/projects/* (创建/列表/删除)
│   │   ├── training.py          # /api/training/* (训练/状态/下载)
│   │   └── visualization.py     # /api/viz/* (raw 数据/feedback 数据)
│   │
│   ├── services/                # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── storage.py           # [新] 本地文件存储 (替代 Supabase)
│   │   ├── csv_parser.py        # [已有] CSV 解析 + 峰值检测
│   │   ├── feature_extractor.py # [已有] 40 维特征提取
│   │   └── model_trainer.py     # [新] sklearn 训练 + CoreML 导出
│   │
│   └── storage/                 # [自动创建] 数据文件
│       ├── projects/            # 项目 JSON
│       ├── sessions/            # Session 元数据 JSON
│       ├── csv_files/           # 上传的 CSV
│       ├── models/              # 训练好的模型 (.pkl)
│       └── training_runs/       # 训练记录 JSON
│
├── frontend/                    # Streamlit 前端
│   ├── app.py                   # Dashboard 主页
│   ├── requirements.txt         # 前端依赖
│   ├── .streamlit/
│   │   └── config.toml          # 主题配置 (橙色)
│   └── pages/
│       ├── 1_📊_Projects.py     # 项目管理
│       ├── 2_📤_Upload.py       # CSV 上传
│       ├── 3_📈_Visualize.py    # 数据可视化
│       ├── 4_🧹_Clean.py       # 数据清洗
│       └── 5_🤖_Train.py       # 模型训练
│
└── data/                        # 测试 CSV 文件
    ├── {id}_create_test.csv     # 模拟 Raw IMU (6000 行)
    └── {id}_feedback_test.csv   # 模拟 Feedback (25 行)
```

---

## 17. 日常启动方法

### 方法 A: 两个终端（推荐）

**终端 1 - 后端**:
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate tennis-web
cd ~/Desktop/tennis_coach_JT/coachWeb/tennis-coach-web/backend
uvicorn main:app --reload
```

**终端 2 - 前端**:
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate tennis-web
cd ~/Desktop/tennis_coach_JT/coachWeb/tennis-coach-web/frontend
streamlit run app.py
```

**打开浏览器**:
- 前端界面: http://localhost:8501
- API 文档: http://localhost:8000/docs

### 方法 B: 一键启动

```bash
cd ~/Desktop/tennis_coach_JT/coachWeb/tennis-coach-web
bash start.sh
```

### 停止服务

- 两个终端方式: 每个终端按 `Ctrl+C`
- 一键脚本方式: 按一次 `Ctrl+C`

---

## 附录: 已有的保留文件说明

以下文件是项目骨架阶段就已写好的，本次构建中 **没有修改**，直接复用：

| 文件 | 作用 |
|------|------|
| `backend/services/csv_parser.py` | CSV 解析：parse_raw_csv, parse_feedback_csv, validate_csv_format, detect_peaks, segment_window |
| `backend/services/feature_extractor.py` | 40 维特征提取：extract_features, batch_extract_features, get_feature_names |
| `backend/routers/__init__.py` | 路由包标识 |
| `frontend/.streamlit/config.toml` | Streamlit 主题配置 |
| `backend/.env.example` | 环境变量模板 |
