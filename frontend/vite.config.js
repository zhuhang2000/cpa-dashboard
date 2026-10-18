import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// `npm run dev` proxies /api to the Python backend; `npm run build` emits dist/,
// which the backend serves directly (see backend/config.json -> frontend_dir).
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:18400', changeOrigin: false },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
})
