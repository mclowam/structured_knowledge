import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': { target: 'http://localhost:8001', changeOrigin: true },
      '/api': { target: 'http://localhost:8002', changeOrigin: true },
    },
  },
})
