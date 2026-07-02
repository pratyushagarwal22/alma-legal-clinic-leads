# syntax=docker/dockerfile:1

# Multi-stage build for the Next.js web app.
#
# Because NEXT_PUBLIC_* values are inlined into the browser bundle at BUILD time,
# the API base URL the browser uses is provided as a build ARG (defaults to the
# host-mapped API at http://localhost:8000). See docker-compose.yml for wiring.

# --- deps: install node modules for the container platform -------------------
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- builder: compile the production build -----------------------------------
FROM node:20-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# API base URL the BROWSER calls. Baked into the client bundle at build time.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- runner: minimal image that serves the built app ------------------------
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.mjs ./next.config.mjs

EXPOSE 3000

# Bind all interfaces so the mapped port is reachable from the host.
CMD ["node_modules/.bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
