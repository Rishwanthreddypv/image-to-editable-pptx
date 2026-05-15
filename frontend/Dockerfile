FROM node:20-alpine AS base
WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable pnpm

# Copy workspace config and package.jsons
COPY pnpm-workspace.yaml ./
COPY package.json ./
COPY frontend/package.json ./frontend/
COPY shared/ ./shared/

# Install dependencies (ignoring shared/package.json if not present)
RUN pnpm install

# Copy frontend source
COPY frontend ./frontend

# Build frontend
WORKDIR /app/frontend
RUN pnpm build

EXPOSE 3000

# Start Next.js
CMD ["pnpm", "start"]
