import type { CreateClientConfig } from "./client/client";

const _raw = import.meta.env.VITE_API_BASE_URL ?? "/api";
const DEFAULT_BASE_URL = _raw.endsWith("/") ? _raw.slice(0, -1) : _raw;

export function apiUrl(path: string): string {
	return `${DEFAULT_BASE_URL}${path}`;
}

export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseURL: config.baseURL ?? DEFAULT_BASE_URL,
	headers: {
		"Content-Type": "application/json",
		...config.headers,
	},
	timeout: config.timeout ?? 15000,
});
