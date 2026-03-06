import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import compression from 'vite-plugin-compression'

export default defineConfig({
  plugins: [
    react(),
    // Gzip compression plugin for build output
    compression({
      verbose: true,
      disable: false,
      threshold: 1000, // Only compress files > 1KB
      algorithm: 'gzip',
      ext: '.gz',
    }),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
        // Enable compression for requests
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Accept-Encoding', 'gzip, deflate');
          });
        },
      }
    }
  },
  // Build optimizations for production
  build: {
    rollupOptions: {
      output: {
        // Code splitting for better caching
        manualChunks: {
          'vendor': [
            'react',
            'react-dom',
          ],
        }
      }
    },
    // Enable minification for smaller bundle
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
      }
    }
  }
})
