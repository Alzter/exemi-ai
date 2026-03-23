import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const extensionBuild = process.env.EXEMI_EXTENSION_BUILD === '1'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: extensionBuild ? './' : '/',
  ...(extensionBuild
    ? {
        build: {
          outDir: '../exemi-extension/dist/exemi-frontend',
          emptyOutDir: false,
        },
      }
    : {}),
})
