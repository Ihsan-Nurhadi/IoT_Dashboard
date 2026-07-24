# Stage 1: Build aplikasi React/Vite
FROM node:22-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve menggunakan Nginx
FROM nginx:stable-alpine
# Hapus file default nginx yang menyebabkan halaman "Welcome to Nginx"
RUN rm -rf /usr/share/nginx/html/*
# Salin hasil build dari stage pertama ke folder publik Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Salin konfigurasi Nginx khusus untuk React Router (try_files)
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]