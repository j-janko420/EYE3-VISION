FROM node:22-alpine
RUN apk add --no-cache ffmpeg
WORKDIR /app
COPY . .
ENV HOST=0.0.0.0 PORT=8080 MEDIA_DIR=/media
VOLUME /media
EXPOSE 8080
# A random access token is printed at startup unless EYE3_TOKEN is set (required off-loopback).
CMD ["node", "server.js"]
