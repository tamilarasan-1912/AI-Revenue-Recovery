import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use the Vercel same-origin /api proxy in production so browser requests do not
// depend on Render CORS configuration. Local development still uses Vite's
// /api proxy to the backend container.
const productionApi = '/api'

export default defineConfig({
  plugins: [react()],
  define: {
    // Keep the frontend API path same-origin in deployed builds.
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
