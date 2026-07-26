# Docker Build & Publish Guide

## Step 1: Build Image Locally
```bash
docker build -t jotalbot/aios:latest .
docker build -t jotalbot/aios:1.0.0 .
```

## Step 2: Test Locally
```bash
docker run -p 8080:8080 jotalbot/aios:latest
# Open http://localhost:8080
```

## Step 3: Login to Docker Hub
```bash
docker login -u jotalbot
# Enter password
```

## Step 4: Push to Docker Hub
```bash
docker push jotalbot/aios:latest
docker push jotalbot/aios:1.0.0
```

## Step 5: Deploy to Server
```bash
ssh root@your-server
docker pull jotalbot/aios:latest
docker-compose up -d
```

## Verify Deployment
```bash
curl http://your-server:8080/health
# Expected: {"status": "healthy"}
```
