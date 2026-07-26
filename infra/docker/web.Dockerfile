FROM node:22-alpine AS dependencies
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci

FROM dependencies AS development
COPY apps/web ./

FROM development AS build
RUN npm run build

FROM nginx:1.27-alpine
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
