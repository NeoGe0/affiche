import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react({

      babel: { plugins: [['babel-plugin-react-compiler', { target: '19' }]] },
    }),
  ],
  server: {
    port: 3000,
    proxy: {
      '/affiche': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],

    globals: false,

    css: false,
    restoreMocks: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
