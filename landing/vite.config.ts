/// <reference types="vitest/config" />
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	resolve: {
		conditions: ['browser'],
	},
	test: {
		globals: true, // required for @testing-library/jest-dom matchers in test-setup.ts
		environment: 'jsdom',
		setupFiles: ['src/test-setup.ts'],
		include: ['src/**/*.test.ts'],
	},
});
