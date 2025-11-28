<div align="center">
  <a href="#">
    <img src="https://raw.githubusercontent.com/LuoXi-Project/LX_Project_Template/refs/heads/main/ui/logo.png" width="240" height="240" alt="点我跳转文档">
  </a>
</div>

<div align="center">

# ✨ 洛曦 云旅Agent ✨

[![][python]][python]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]
[![][github-forks-shield]][github-forks-link]
[![][github-issues-shield]][github-issues-link]  
[![][github-contributors-shield]][github-contributors-link]
[![][github-license-shield]][github-license-link]

</div>

# LX SkyRoam Agent - 智能旅游攻略生成器

一个基于AI的智能旅游攻略生成系统，提供个性化的旅行方案规划。

## 功能特性

- 🤖 **智能Agent**: 基于大语言模型的旅游规划助手
- 🔍 **多源数据**: 整合航班、酒店、景点、天气等多维度信息
- 🕷️ **智能爬虫**: 自动补充缺失数据，确保信息完整性
- 📊 **数据清洗**: 智能甄别和可信度评分系统
- 🗺️ **可视化展示**: 地图集成和方案对比视图
- 📱 **响应式设计**: 支持多设备访问
- 🔄 **实时更新**: 后台任务持续更新数据

## 技术架构

### 后端
- **FastAPI**: 高性能API框架
- **SQLAlchemy**: ORM数据库操作
- **Celery**: 异步任务处理
- **Redis**: 缓存和消息队列
- **MCP Tools**: 模型控制协议工具集成

### 前端
- **React**: 现代化前端框架
- **TypeScript**: 类型安全
- **Tailwind CSS**: 样式框架
- **Leaflet**: 地图组件
- **Ant Design**: UI组件库

### AI & 数据
- **OpenAI API**: 大语言模型
- **Scrapy**: 网页爬虫
- **Pandas**: 数据处理
- **NumPy**: 数值计算

## 项目结构

```
LX_SkyRoam_Agent/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── mcp/            # MCP工具
│   │   ├── models/         # 数据模型
│   │   ├── platforms/      # 平台相关(小红书爬虫)
│   │   ├── services/       # 业务逻辑
│   │   ├── tasks/          # celery异步任务
│   │   ├── tools/          # 工具
│   ├── scripts/            # 脚本
│   ├── tests/              # 测试
│   ├── uploads/            # 上传文件目录（挂载静态文件）
│   ├── logs/               # 日志目录
│   ├── .gitignore
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example        # 环境变量示例
│   ├── .env                # 环境变量
│   ├── requirements.txt    # 依赖包
│   └── main.py             # 应用入口
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API服务
│   │   └── utils/          # 工具函数
│   ├── package.json
│   └── public/
├── database/              # 数据库相关
│   ├── migrations/        # 数据库迁移
│   └── init.sql
├── docker/               # Docker配置
├── docs/                 # 文档
└── tests/                # 测试文件
```

## 快速开始

### 环境要求
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/en/download)
- [Redis](https://redis.io/download)
- [PostgreSQL](https://www.postgresql.org/download/)

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd LX_SkyRoam_Agent
```

2. 后端设置
```bash
cd backend
pip install -r requirements.txt
```

3. 前端设置
```bash
cd frontend
npm install
```

4. 环境配置
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和API密钥
```

5. 启动服务
```bash
# 启动后端
cd backend && uvicorn main:app

# 启动Celery Worker
cd backend && celery -A app.core.celery worker --loglevel=info

# 启动前端
cd frontend && npm start

# 启动高德API服务
cd backend && python mcp_http_server_amap.py

# 启动小红书爬虫服务
cd backend && python xhs_api_server.py

```

### Windows 一键启动

- 运行根目录中的 `start-all-win.bat`，脚本会自动激活 `skyroam` Conda 环境，并在独立窗口中依次启动 FastAPI、Celery、前端、高德 API 以及小红书服务。

## 使用说明

1. 在前端输入旅行需求（目的地、天数、偏好、预算）
2. AI Agent分析需求并收集相关信息
3. 系统生成多个旅行方案供选择
4. 用户可以调整和细化方案
5. 导出最终方案（PDF、图片、分享链接）

## ⭐️ Star 经历

[![Star History Chart](https://api.star-history.com/svg?repos=Ikaros-521/LX_SkyRoam_Agent&type=Date)](https://star-history.com/#Ikaros-521/LX_SkyRoam_Agent&Date)

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 许可证

GPL3.0 License

[python]: https://img.shields.io/badge/python-3.10+-blue.svg?labelColor=black
[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-black?style=flat-square
[github-action-release-link]: https://github.com/actions/workflows/Ikaros-521/LX_SkyRoam_Agent/release.yml
[github-action-release-shield]: https://img.shields.io/github/actions/workflow/status/Ikaros-521/LX_SkyRoam_Agent/release.yml?label=release&labelColor=black&logo=githubactions&logoColor=white&style=flat-square
[github-action-test-link]: https://github.com/actions/workflows/Ikaros-521/LX_SkyRoam_Agent/test.yml
[github-action-test-shield]: https://img.shields.io/github/actions/workflow/status/Ikaros-521/LX_SkyRoam_Agent/test.yml?label=test&labelColor=black&logo=githubactions&logoColor=white&style=flat-square
[github-codespace-link]: https://codespaces.new/Ikaros-521/LX_SkyRoam_Agent
[github-codespace-shield]: https://github.com/codespaces/badge.svg
[github-contributors-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/graphs/contributors
[github-contributors-shield]: https://img.shields.io/github/contributors/Ikaros-521/LX_SkyRoam_Agent?color=c4f042&labelColor=black&style=flat-square
[github-forks-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/network/members
[github-forks-shield]: https://img.shields.io/github/forks/Ikaros-521/LX_SkyRoam_Agent?color=8ae8ff&labelColor=black&style=flat-square
[github-issues-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/issues
[github-issues-shield]: https://img.shields.io/github/issues/Ikaros-521/LX_SkyRoam_Agent?color=ff80eb&labelColor=black&style=flat-square
[github-license-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/blob/main/LICENSE
[github-license-shield]: https://img.shields.io/github/license/Ikaros-521/LX_SkyRoam_Agent?color=white&labelColor=black&style=flat-square
[github-release-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/releases
[github-release-shield]: https://img.shields.io/github/v/release/Ikaros-521/LX_SkyRoam_Agent?color=369eff&labelColor=black&logo=github&style=flat-square
[github-releasedate-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/releases
[github-releasedate-shield]: https://img.shields.io/github/release-date/Ikaros-521/LX_SkyRoam_Agent?labelColor=black&style=flat-square
[github-stars-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/network/stargazers
[github-stars-shield]: https://img.shields.io/github/stars/Ikaros-521/LX_SkyRoam_Agent?color=ffcb47&labelColor=black&style=flat-square
[pr-welcome-link]: https://github.com/Ikaros-521/LX_SkyRoam_Agent/pulls
[pr-welcome-shield]: https://img.shields.io/badge/%F0%9F%A4%AF%20PR%20WELCOME-%E2%86%92-ffcb47?labelColor=black&style=for-the-badge
[profile-link]: https://github.com/LuoXi-Project
