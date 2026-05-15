FROM docker.m.daocloud.io/library/node:22.13.1-alpine AS builder
WORKDIR /app
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install --include=optional
COPY . .
RUN npm run build

FROM docker.m.daocloud.io/library/nginx:1.27.2-alpine
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
RUN chmod -R a+rX /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
