import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Allow access from all network interfaces
    port: 3000,
    strictPort: true, // Fail if port is in use
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/clips': {
        target: 'https://d2qqs9uhgc4wdq.cloudfront.net',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/clips/, '/clips'),
      }
    }
  }
})
