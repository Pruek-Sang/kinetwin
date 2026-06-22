# KineTwin frontend image (isolated name: kinetwin-frontend).
# Multi-stage: build the Vite app, serve the static bundle with nginx, and
# proxy /analyze* and /health to the backend container.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Bake the backend URL into the bundle (set at build time for Cloud Run).
# Empty -> same-origin (works with the Vite dev proxy / nginx in compose).
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# nginx-unprivileged runs as non-root and listens on 8080 -> Cloud Run friendly.
FROM nginxinc/nginx-unprivileged:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
