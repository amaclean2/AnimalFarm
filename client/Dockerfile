FROM nginx:alpine

# Pass full URLs at build time, e.g.:
#   --build-arg API_URL=https://example.com
#   --build-arg WS_URL=wss://example.com/ws
ARG API_URL=http://localhost:8000
ARG WS_URL=ws://localhost:8000/ws

COPY . /usr/share/nginx/html

RUN sed -i "s|http://localhost:8000|${API_URL}|g" /usr/share/nginx/html/scripts/main.js && \
    sed -i "s|ws://localhost:8000/ws|${WS_URL}|g" /usr/share/nginx/html/scripts/main.js

EXPOSE 80
