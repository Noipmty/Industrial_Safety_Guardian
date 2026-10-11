# ---------- 阶段 1：构建 ----------
FROM node:20-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ---------- 阶段 2：nginx 静态资源 ----------
FROM nginx:1.27-alpine

# nginx.conf 由 docker-compose 挂载；此处仅复制构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1
