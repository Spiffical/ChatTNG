import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 3000,
      watch: {
        usePolling: true,
      },
      strictPort: true, // Fail if port is in use
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET,
          changeOrigin: true,
          secure: false
        },
        '/clips': {
          target: 'https://d2qqs9uhgc4wdq.cloudfront.net',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/clips/, '/clips'),
        }
      }
    },
    optimizeDeps: {
      force: true,
      esbuildOptions: {
        target: 'esnext'
      }
    },
    build: {
      target: 'esnext'
    }
  }
})
