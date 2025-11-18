FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY src ./src

# Build TypeScript
RUN npm run build

# Set default environment variables
ENV MCP_PORT=3000
ENV MCP_HOST=0.0.0.0
ENV GPG_API_BASE=http://gpg-webservice:5000

# Expose MCP HTTP port
EXPOSE 3000

# Run HTTP MCP server by default
CMD ["node", "dist/http-server.js"]
