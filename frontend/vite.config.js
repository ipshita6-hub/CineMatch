import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  if (process.env.VERCEL && !/^https:\/\//.test(env.VITE_API_URL || '')) {
    throw new Error('Set VITE_API_URL to the public HTTPS Render backend URL in Vercel.')
  }
  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173 },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/__tests__/setup.js',
    },
  }
})
