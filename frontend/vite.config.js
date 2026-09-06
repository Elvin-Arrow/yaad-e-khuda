import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      // python -m prayer_sync serve runs the API on :8000 in dev; the
      // browser only ever talks to Vite's :5173, so no CORS is needed.
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
