import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const productionApi = 'https://recoverai-api-zwr9.onrender.com/api'

export default defineConfig({
  plugins: [react()],
  define: {
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
