# =============================================================
# SparkLaw — Frontend Dockerfile (Production)
# Multi-stage build · node:20.18.3-bookworm-slim · non-root user
# =============================================================

# ── Stage 1: dependency installer ────────────────────────────
FROM node:20.18.3-bookworm-slim AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile


# ── Stage 2: builder ─────────────────────────────────────────
FROM node:20.18.3-bookworm-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build args for injecting API URL at build time
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build


# ── Stage 3: runtime ─────────────────────────────────────────
FROM node:20.18.3-bookworm-slim AS runtime

LABEL org.opencontainers.image.title="SparkLaw Frontend"
LABEL org.opencontainers.image.description="Chinese Legal AI Frontend — Next.js"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Install wget for healthcheck (slim has no wget by default)
RUN apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 1001 nodejs \
    && useradd --system --uid 1001 --gid nodejs nextjs

# Copy only what's needed to run
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000 || exit 1

CMD ["node", "server.js"]
