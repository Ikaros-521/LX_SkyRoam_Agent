#!/bin/bash

echo "🚀 启动 LX SkyRoam Agent 开发环境..."

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 未安装，请先安装 Python 3.10+"
    exit 1
fi

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 18+"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p backend/logs
mkdir -p backend/uploads

# 启动后端服务
echo "🐍 启动后端服务..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 启动前端服务
echo "⚛️ 启动前端服务..."
cd frontend
npm install
REACT_APP_API_BASE_URL=http://localhost:8001/api/v1 npm start &
FRONTEND_PID=$!
cd ..

# 等待前端启动
echo "⏳ 等待前端启动..."
sleep 5

# 显示访问信息
echo ""
echo "✅ LX SkyRoam Agent 开发环境启动完成！"
echo ""
echo "📱 前端应用: http://localhost:3000"
echo "🔧 后端API: http://localhost:8001"
echo "📚 API文档: http://localhost:8001/docs"
echo ""
echo "📝 注意事项:"
echo "   - 确保PostgreSQL数据库正在运行"
echo "   - 确保Redis服务正在运行"
echo "   - 在backend目录下创建.env文件配置环境变量"
echo ""
echo "🛑 停止服务: Ctrl+C"

# 等待用户中断
trap "echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
