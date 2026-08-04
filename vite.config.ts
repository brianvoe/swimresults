import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // strictPort so a stray process on 3333 fails loudly instead of silently
  // moving the site to another port.
  server: { port: 3333, strictPort: true },
  preview: { port: 3333, strictPort: true },
})
