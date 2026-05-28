import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  base: './',
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/proxy': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => path.replace(/^\/proxy/, '')
      }
    }
  },
  optimizeDeps: {
    exclude: [
      'react-native',
      '@expo/vector-icons',
      '@react-native-firebase/messaging',
      '@react-native-firebase/app',
      '@react-native/assets-registry'
    ]
  },
  resolve: {
    alias: {
      'react-native': '/src/shims/react-native.js',
      '@expo/vector-icons': '/src/shims/expo-vector-icons.js',
      '@react-native-firebase/messaging': '/src/shims/rn-firebase-messaging.js',
      '@react-native-firebase/app': '/src/shims/rn-firebase-app.js',
      '@react-native/assets-registry': '/src/shims/rn-assets-registry.js'
    }
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'BarberMove - Seu Barbeiro a um Toque',
        short_name: 'BarberMove',
        description: 'Conecte-se com barbeiros profissionais ou ofereça seus serviços',
        theme_color: '#1f2937',
        background_color: '#111827',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        cleanupOutdatedCaches: true,
        skipWaiting: true,
        clientsClaim: true
      }
    })
  ]
})
