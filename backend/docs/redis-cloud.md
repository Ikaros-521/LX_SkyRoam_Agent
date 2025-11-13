# 云 Redis 配置指引

创建地址：https://cloud.redis.io/  

## 环境变量

在 `backend/.env` 中新增或设置以下项：

```
REDIS_USE_TLS=true
REDIS_HOST=your-cloud-redis-host
REDIS_PORT=your-cloud-redis-port
REDIS_USERNAME=default
REDIS_PASSWORD=your-password
REDIS_DB=0
# 或直接使用完整 URL（优先于以上分项）：
# REDIS_URL=rediss://default:your-password@your-cloud-redis-host:your-cloud-redis-port/0

# 缓存开关（出问题时关闭以绕过缓存逻辑）
MAP_CACHE_ENABLED=true
```

注意：
- 使用云 Redis（TLS），请将 `REDIS_USE_TLS=true` 或采用 `rediss://` 协议的完整 URL。
- 切勿将真实密码写入代码库。通过 `.env` 提供并在部署环境注入。
- 如 Redis 写入异常或持久化失败，可将 `MAP_CACHE_ENABLED=false` 暂时关闭缓存以保证业务可用。

## 连接示例（Python）

```
import redis

r = redis.Redis(
    host="your-cloud-redis-host",
    port=your_cloud_redis_port,
    username="default",
    password="your-password",
    ssl=True,
    decode_responses=True,
)
print(r.ping())
```

## 常见问题

- 若出现 RDB 持久化失败，请确保云服务端可写且不误配置 `dir/dbfilename`；使用云服务时通常无需自定义本地持久化路径。
- 若限流/缓存写失败，可暂时关闭缓存（`MAP_CACHE_ENABLED=false`）或关闭输入提示（`MAP_INPUT_TIPS_ENABLED=false`）。
