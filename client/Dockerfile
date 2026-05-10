FROM nginx:alpine

# Replace hardcoded localhost:8000 with the real API host at build time.
# Pass --build-arg API_HOST=<droplet-ip>:8000 when building for production.
ARG API_HOST=localhost:8000

COPY . /usr/share/nginx/html

RUN sed -i "s|localhost:8000|${API_HOST}|g" /usr/share/nginx/html/scripts/main.js

EXPOSE 80
