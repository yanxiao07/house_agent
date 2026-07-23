import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
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
