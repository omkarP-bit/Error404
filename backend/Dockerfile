# Optimized multi-stage build
FROM node:18-alpine as deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production --no-audit --no-fund && npm cache clean --force

FROM node:18-alpine as runner
WORKDIR /app

# Install wget for healthcheck
RUN apk add --no-cache wget

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Copy dependencies
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy application code
COPY --chown=nextjs:nodejs src/ ./src/
COPY --chown=nextjs:nodejs server.js package*.json ./

USER nextjs

EXPOSE 3000

# Add health endpoint
ENV NODE_ENV=production

CMD ["node", "server.js"]
