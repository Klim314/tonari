import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const proxyTarget =
	process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8087";

export default defineConfig({
	plugins: [react()],
	server: {
		host: true,
		port: 5173,
		watch: {
			usePolling: true,
			interval: 100,
		},
		proxy: {
			"/api": {
				target: proxyTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, ""),
			},
		},
	},
	preview: {
		port: 4173,
	},
});
