import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // GitHub Pages serves project sites from /<repository-name>/ rather than /.
  // Local development keeps the root path, while the deployment workflow sets it.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue'],
          three: ['three'],
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
