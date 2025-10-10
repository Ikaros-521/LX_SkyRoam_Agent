@echo off
chcp 65001 >nul

echo 🚀 启动 LX SkyRoam Agent 开发环境...

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查Node.js是否安装
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装，请先安装 Node.js 18+
    pause
    exit /b 1
)

REM 创建必要的目录
echo 📁 创建必要的目录...
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\uploads" mkdir backend\uploads

REM 启动后端服务
echo 🐍 启动后端服务...
start "Backend" cmd /k "cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

REM 等待后端启动
echo ⏳ 等待后端启动...
timeout /t 5 /nobreak >nul

REM 启动前端服务
echo ⚛️ 启动前端服务...
start "Frontend" cmd /k "cd frontend && npm install && set \"REACT_APP_API_BASE_URL=http://localhost:8001/api/v1\" && npm start"

REM 等待前端启动
echo ⏳ 等待前端启动...
timeout /t 5 /nobreak >nul

REM 显示访问信息
echo.
echo ✅ LX SkyRoam Agent 开发环境启动完成！
echo.
echo 📱 前端应用: http://localhost:3000
echo 🔧 后端API: http://localhost:8001
echo 📚 API文档: http://localhost:8001/docs
echo.
echo 📝 注意事项:
echo    - 确保PostgreSQL数据库正在运行
echo    - 确保Redis服务正在运行
echo    - 在backend目录下创建.env文件配置环境变量
echo.
echo 🛑 停止服务: 关闭对应的命令行窗口
echo.

pause
