# ---- 前端 Dockerfile（多阶段构建）----

# 阶段 1：构建
FROM node:22-alpine AS builder

RUN corepack enable pnpm

WORKDIR /app

# 复制依赖声明（利用缓存层）
COPY web/package.json web/pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

# 复制源码并构建
COPY web/ ./

RUN pnpm build

# 阶段 2：运行（Nginx 托管静态文件）
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
