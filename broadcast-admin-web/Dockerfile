FROM node:24-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# If VITE_BROADCAST_API_URL is not provided, will use /api proxy path
ARG VITE_PREVIEW_MODE=false
ENV VITE_PREVIEW_MODE=${VITE_PREVIEW_MODE}
ARG VITE_BROADCAST_API_URL
ENV VITE_BROADCAST_API_URL=${VITE_BROADCAST_API_URL}

RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

