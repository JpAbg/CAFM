import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from '../../../frappe-ui/vite/index.js';
import proxyOptions from './proxyOptions.js';

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [vue(), frappeui({ frappeProxy: false, jinjaBootData: false, buildConfig: false })],
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
		outDir: '../cafm/public/dashboard',
		emptyOutDir: true,
		target: 'es2015',
	},
});
