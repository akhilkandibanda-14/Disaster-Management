# =============================================================================
# SafeMap AI — Frontend Production Multi-Stage Dockerfile
# Stage 1: Build static assets using Node.js
# Stage 2: Serve optimized bundle using lightweight Alpine Nginx
# =============================================================================

# --- Stage 1: Build Environment ---
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests first to leverage Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source files
COPY index.html ./
COPY vite.config.js ./
COPY src/ ./src/

# Build production bundle
RUN npm run build

# --- Stage 2: Production Web Server ---
FROM nginx:alpine AS runner

# Remove default nginx site
RUN rm -rf /usr/share/nginx/html/*

# Copy built artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy optimized nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Health check probing the /healthz endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
