# Multi-stage build: stage 1 builds the frontend
FROM node:18-alpine AS builder

# Enable corepack to support pnpm
RUN corepack enable

# Set working directory
WORKDIR /app

# Copy package.json and pnpm-lock.yaml (if present)
COPY package.json pnpm-lock.yaml* ./

# Install dependencies including dev dependencies for build
RUN pnpm install

# Copy source code
COPY . .

# Set build-time environment variable, can be overridden by build arg
ARG VITE_SERVER_URL=http://localhost:8000
ENV VITE_SERVER_URL=${VITE_SERVER_URL}

# Build application
RUN pnpm run build

# Stage 2: Runtime environment
FROM node:18-alpine AS runtime

# Enable corepack to support pnpm
RUN corepack enable

# Set working directory
WORKDIR /app

# Install production dependencies only
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --prod

# Copy build artifacts from builder stage
COPY --from=builder /app/dist ./dist
COPY server.js ./

# Expose port
EXPOSE 5000

# Startup command
CMD ["node", "server.js"]