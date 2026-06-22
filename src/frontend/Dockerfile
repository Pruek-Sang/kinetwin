# KineTwin frontend image (isolated name: kinetwin-frontend).
# Multi-stage: build the Vite app, serve the static bundle with nginx, and
# proxy /analyze* and /health to the backend container.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
