
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// Vite configuration for the React frontend.
// React handles JSX and Tailwind processes utility classes.
export default defineConfig({
  devtools: {
    // Enable DevTools only during development.
    apply: 'serve',
  },

  plugins: [
    react(),
    tailwindcss(),
  ],
})
