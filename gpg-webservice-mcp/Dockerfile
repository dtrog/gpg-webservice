FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY src ./src

# Build TypeScript
RUN npm run build

# Remove devDependencies after build to reduce image size
RUN npm prune --production

# Set default environment variables
ENV MCP_PORT=3000
ENV MCP_HOST=0.0.0.0
ENV GPG_API_BASE=http://localhost:5555

# Expose MCP HTTP port
EXPOSE 3000

# Run HTTP MCP server by default
CMD ["node", "dist/http-server.js"]
