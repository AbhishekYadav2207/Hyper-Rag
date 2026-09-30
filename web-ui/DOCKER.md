# Hyper-RAG Web UI Docker Deployment Guide

This document describes how to deploy the Hyper-RAG Web UI using Docker and Docker Compose.

## Architecture Overview

The application consists of two main services:
- **Backend**: FastAPI application serving on port 8000.
- **Frontend**: React application built and served on port 5000.
- **Nginx**: Optional reverse proxy coordinating traffic.

## Quick Start

### Using Docker Compose (Recommended)

Run from the `web-ui` directory:

```bash
# Build and start services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the application:
- Frontend: `http://localhost:5000`
- Backend API: `http://localhost:8000`

### Building and Running Individually

#### Backend

```bash
cd backend
docker build -t hyperrag-backend .
docker run -p 8000:8000 -v $(pwd)/hyperrag_cache:/app/hyperrag_cache hyperrag-backend
```

#### Frontend

```bash
cd frontend
docker build -t hyperrag-frontend .
docker run -p 5000:5000 hyperrag-frontend
```

## Configuration

### Environment Variables

#### Frontend
- `VITE_SERVER_URL`: Backend API URL (build-time variable)
  - Default: `http://localhost:8000` (local dev)
  - Docker Compose: `http://backend:8000`

#### Backend
- `PYTHONPATH`: Python module search path.

## Troubleshooting

1. **Port Conflicts**: Ensure ports 8000 and 5000 are not in use.
2. **Permissions**: Ensure Docker has read/write access to mounted volumes.
3. **Logs**: Check container output via `docker-compose logs -f backend`.