import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        // Use Docker service name 'backend' when running in Docker Compose
        // For local development outside Docker, change to 'http://localhost:8000'
        target: 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => {
          // Rewrite /api/health to /health, but keep /api/v1/* as is
          if (path === '/api/health') {
            return '/health'
          }
          return path
        },
      },
    },
  },
})
