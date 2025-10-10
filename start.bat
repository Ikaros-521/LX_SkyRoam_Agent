@echo off
chcp 65001 >nul

echo 🚀 启动 LX SkyRoam Agent...

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker
    pause
    exit /b 1
)

REM 检查Docker Compose是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    pause
    exit /b 1
)

REM 创建必要的目录
echo 📁 创建必要的目录...
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads

REM 复制环境配置文件
if not exist ".env" (
    echo 📋 复制环境配置文件...
    copy env.example .env
    echo ⚠️  请编辑 .env 文件，配置您的API密钥和其他设置
)

REM 启动服务
echo 🐳 启动 Docker 服务...
docker-compose up -d

REM 等待服务启动
echo ⏳ 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 🔍 检查服务状态...
docker-compose ps

REM 显示访问信息
echo.
echo ✅ LX SkyRoam Agent 启动完成！
echo.
echo 📱 前端应用: http://localhost:3000
echo 🔧 后端API: http://localhost:8000
echo 📚 API文档: http://localhost:8000/docs
echo 🌸 Celery监控: http://localhost:5555
echo.
echo 📝 日志查看:
echo    docker-compose logs -f backend
echo    docker-compose logs -f frontend
echo.
echo 🛑 停止服务:
echo    docker-compose down
echo.

pause
