FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production image
FROM node:20-alpine

WORKDIR /app

# Install a simple HTTP server
RUN npm install -g http-server

# Copy built files from builder
COPY --from=builder /app/dist ./dist

EXPOSE 3000

# Serve the application
CMD ["http-server", "dist", "-p", "3000"]
