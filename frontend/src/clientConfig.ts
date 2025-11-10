import type { CreateClientConfig } from "./client/client";

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseURL: config.baseURL ?? DEFAULT_BASE_URL,
	headers: {
		"Content-Type": "application/json",
		...config.headers,
	},
	timeout: config.timeout ?? 15000,
});
