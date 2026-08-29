import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Production backend used by the deployed RecoverAI frontend.
// Vercel must rebuild this file; otherwise an older bundle can fall back to localhost.
const productionApi = 'https://recoverai-api-zwr9.onrender.com/api'

export default defineConfig({
  plugins: [react()],
  define: {
    // Keep the production endpoint deterministic even when Vercel has no VITE_API_URL variable.
    'import.meta.env.VITE_API_URL': JSON.stringify(productionApi),
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: 'http://backend:8000', changeOrigin: true },
    },
  },
})
