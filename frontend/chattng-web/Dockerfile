FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Clean Vite cache
RUN rm -rf node_modules/.vite

# Copy the rest of the application code
COPY . .

# Expose port 3000
EXPOSE 3000

# Start the development server with host and force option
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--force"] 