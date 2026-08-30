import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const configuredApi = env.VITE_API_URL?.trim()
  const apiBase = !configuredApi || configuredApi === '/api'
    ? '/api'
    : `${configuredApi.replace(/\/$/, '')}/api`

  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_API_URL': JSON.stringify(apiBase),
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        '/api': { target: 'http://backend:8000', changeOrigin: true },
      },
    },
  }
})
