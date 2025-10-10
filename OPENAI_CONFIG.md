# 🤖 OpenAI API 配置指南

## 📋 概述

LX SkyRoam Agent 支持自定义 OpenAI API 地址，允许您使用代理服务、自托管服务或其他兼容的 OpenAI API 端点。

## 🔧 配置选项

### 环境变量配置

在 `.env` 文件中配置以下参数：

```env
# OpenAI API密钥 (必需)
OPENAI_API_KEY=your-openai-api-key-here

# OpenAI API地址 (可选，默认为官方地址)
OPENAI_API_BASE=https://api.openai.com/v1

# OpenAI模型 (可选，默认为 gpt-4-turbo-preview)
OPENAI_MODEL=gpt-4-turbo-preview

# 最大令牌数 (可选，默认为 4000)
OPENAI_MAX_TOKENS=4000

# 温度参数 (可选，默认为 0.7)
OPENAI_TEMPERATURE=0.7

# API超时时间 (可选，默认为 60秒)
OPENAI_TIMEOUT=60

# 最大重试次数 (可选，默认为 3次)
OPENAI_MAX_RETRIES=3
```

## 🌐 支持的API地址类型

### 1. 官方OpenAI API
```env
OPENAI_API_BASE=https://api.openai.com/v1
```

### 2. 代理服务
```env
# 使用代理服务
OPENAI_API_BASE=https://api.openai-proxy.com/v1
OPENAI_API_BASE=https://your-proxy-domain.com/v1
```

### 3. 自托管服务
```env
# 使用自托管的OpenAI兼容服务
OPENAI_API_BASE=https://your-self-hosted-api.com/v1
OPENAI_API_BASE=http://localhost:8000/v1
```

### 4. 其他兼容服务
```env
# 使用其他OpenAI兼容的API服务
OPENAI_API_BASE=https://api.anthropic.com/v1
OPENAI_API_BASE=https://api.cohere.ai/v1
```

## 🚀 使用示例

### 示例1: 使用代理服务
```env
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.openai-proxy.com/v1
OPENAI_MODEL=gpt-4-turbo-preview
```

### 示例2: 使用自托管服务
```env
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_MODEL=gpt-4-turbo-preview
```

### 示例3: 使用其他模型
```env
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.5
```

## 🔍 配置验证

### 1. 检查配置
```bash
curl http://localhost:8000/api/v1/openai/config
```

响应示例：
```json
{
  "status": "success",
  "config": {
    "api_base": "https://api.openai.com/v1",
    "model": "gpt-4-turbo-preview",
    "max_tokens": 4000,
    "temperature": 0.7,
    "timeout": 60,
    "max_retries": 3,
    "has_api_key": true
  }
}
```

### 2. 测试连接
```bash
curl -X POST http://localhost:8000/api/v1/openai/test
```

响应示例：
```json
{
  "status": "success",
  "message": "OpenAI连接测试成功",
  "response": "我是一个AI助手，可以帮助您...",
  "config": {
    "api_base": "https://api.openai.com/v1",
    "model": "gpt-4-turbo-preview"
  }
}
```

## 🛠️ 高级配置

### 1. 自定义超时设置
```env
# 设置更长的超时时间（适用于慢速网络）
OPENAI_TIMEOUT=120

# 设置更短的重试次数（适用于快速失败）
OPENAI_MAX_RETRIES=1
```

### 2. 模型参数调优
```env
# 更保守的响应（降低温度）
OPENAI_TEMPERATURE=0.3

# 更长的响应（增加令牌数）
OPENAI_MAX_TOKENS=6000

# 使用更快的模型
OPENAI_MODEL=gpt-3.5-turbo
```

### 3. 多环境配置
```env
# 开发环境
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=2000

# 生产环境
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=4000
```

## 🔒 安全考虑

### 1. API密钥安全
- 不要在代码中硬编码API密钥
- 使用环境变量存储敏感信息
- 定期轮换API密钥

### 2. 网络安全
- 使用HTTPS协议
- 验证SSL证书
- 配置防火墙规则

### 3. 访问控制
- 限制API访问IP
- 设置访问频率限制
- 监控API使用情况

## 🐛 故障排除

### 常见问题

#### 1. 连接超时
```bash
# 检查网络连接
ping api.openai.com

# 增加超时时间
OPENAI_TIMEOUT=120
```

#### 2. 认证失败
```bash
# 检查API密钥
echo $OPENAI_API_KEY

# 验证API密钥格式
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

#### 3. 模型不可用
```bash
# 检查可用模型
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# 使用备用模型
OPENAI_MODEL=gpt-3.5-turbo
```

### 调试模式

启用详细日志：
```env
LOG_LEVEL=DEBUG
```

查看日志：
```bash
docker-compose logs -f backend
```

## 📚 API参考

### 配置端点
- `GET /api/v1/openai/config` - 获取配置信息
- `POST /api/v1/openai/test` - 测试连接

### 功能端点
- `POST /api/v1/openai/generate-plan` - 生成旅行计划
- `POST /api/v1/openai/analyze-data` - 分析旅行数据
- `POST /api/v1/openai/optimize-plan` - 优化旅行计划

## 🎯 最佳实践

1. **使用环境变量**: 将所有配置存储在环境变量中
2. **测试连接**: 启动前测试API连接
3. **监控使用**: 定期检查API使用情况
4. **备份配置**: 保存配置文件备份
5. **文档记录**: 记录自定义配置说明

---

**🎉 现在您可以灵活配置OpenAI API地址，享受更好的服务体验！**
