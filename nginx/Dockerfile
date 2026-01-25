# nginx/Dockerfile
FROM nginx:stable-alpine

# Hapus default config Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Masukkan config buatan kita
COPY default.conf /etc/nginx/conf.d/