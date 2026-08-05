import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ command, isPreview }) => ({
  plugins: [vue()],
  // Project Pages URL is https://brianvoe.github.io/swimresults/
  base: command === 'build' || isPreview ? '/swimresults/' : '/',
  build: { outDir: 'docs' },
  // strictPort so a stray process on 3333 fails loudly instead of silently
  // moving the site to another port.
  server: { port: 3333, strictPort: true },
  preview: { port: 3333, strictPort: true },
}))
