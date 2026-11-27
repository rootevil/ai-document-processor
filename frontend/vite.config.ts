
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vitest/config'

// Vite configuration for the React frontend.
// Vitest shares this configuration for API integration tests.
export default defineConfig({
  devtools: {
    // Enable DevTools only during development.
    apply: 'serve',
  },

  plugins: [
    react(),
    tailwindcss(),
  ],

  test: {
    // API tests do not need a browser environment.
    environment: 'node',

    // Reset mock call history between tests.
    clearMocks: true,

    // Restore mocked implementations between tests.
    restoreMocks: true,
  },
})
