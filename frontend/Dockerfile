# syntax=docker/dockerfile:1.7
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制package.json和package-lock.json
COPY package*.json ./

# 安装 cnpm 并配置镜像
RUN npm i -g cnpm --registry=https://registry.npmmirror.com && \
    cnpm config set registry https://registry.npmmirror.com

# 使用 cnpm 安装依赖（缓存加速）
RUN --mount=type=cache,target=/root/.npminstall_tarball --mount=type=cache,target=/root/.npm \
    cnpm install

# 复制源代码
COPY . .

# 设置环境变量（CRA 默认端口 3000）
ENV PORT=3000
ENV HOST=0.0.0.0

# 暴露端口
EXPOSE 3000

# 启动命令（开发模式）
CMD ["npm", "start"]
