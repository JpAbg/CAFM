import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { VitePWA } from 'vite-plugin-pwa';
import frappeui from '../../../frappe-ui/vite/index.js';
import proxyOptions from './proxyOptions.js';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
    base: mode === 'capacitor' ? './' : '/assets/cafm/dashboard/',

    plugins: [
        vue(),
        frappeui({ frappeProxy: false, jinjaBootData: false, buildConfig: false }),
		VitePWA({
			registerType: 'autoUpdate',

			manifest: {
				name: 'CAFM Operations',
				short_name: 'CAFM',

				start_url: '/cafm',
				scope: '/',

				display: 'standalone',
				background_color: '#ffffff',
				theme_color: '#ffffff',

				icons: [
				{
					src: '/assets/cafm/dashboard/pwa-192x192.png',
					sizes: '192x192',
					type: 'image/png'
				},
				{
					src: '/assets/cafm/dashboard/pwa-512x512.png',
					sizes: '512x512',
					type: 'image/png'
				}
				]
			},

			workbox: {
				globPatterns: ['**/*.{js,css,html,ico,png,svg}']
			}
			})
	],
	server: {
		port: 8080,
		host: '0.0.0.0',
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(import.meta.dirname, 'src')
		}
	},
	build: {
		outDir: mode === 'capacitor'
                    ? './dist'
                    : '../cafm/public/dashboard',
		emptyOutDir: true,
		target: 'es2015',
	},
}));
