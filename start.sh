#!/bin/bash
# Tennis Coach Web - 启动脚本
# 用法: bash start.sh

echo "🎾 Tennis Coach Web 启动中..."
echo ""

# 检查 conda
if ! command -v conda &> /dev/null; then
    echo "❌ 请先安装 Miniconda: brew install miniconda"
    exit 1
fi

# 检查环境
if ! conda env list | grep -q "tennis-web"; then
    echo "📦 首次运行，创建 Conda 环境..."
    conda create -n tennis-web python=3.11 -y
    eval "$(conda shell.bash hook)"
    conda activate tennis-web
    conda install numpy pandas scikit-learn -y
    pip install fastapi==0.109.0 "uvicorn[standard]==0.27.0" python-multipart==0.0.6 \
        streamlit==1.30.0 plotly==5.18.0 httpx==0.26.0 python-dotenv==1.0.0 \
        pydantic==2.5.3 pydantic-settings==2.1.0 requests==2.31.0
    echo "✅ 环境创建完成"
fi

eval "$(conda shell.bash hook)"
conda activate tennis-web

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔧 启动后端 (FastAPI)..."
cd "$PROJECT_DIR/backend"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 2

echo "🖥️  启动前端 (Streamlit)..."
cd "$PROJECT_DIR/frontend"
streamlit run app.py --server.port 8501 &
FRONTEND_PID=$!

echo ""
echo "=================================="
echo "✅ 启动完成！"
echo ""
echo "  前端: http://localhost:8501"
echo "  后端: http://localhost:8000/docs"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "=================================="

# 等待退出
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
