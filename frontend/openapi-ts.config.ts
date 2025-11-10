import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
	input: "./openapi.json",
	output: {
		path: "./src/client",
		clean: true,
	},
	plugins: [
		"@hey-api/typescript",
		{
			name: "@hey-api/sdk",
			asClass: true,
		},
		{
			name: "@hey-api/client-axios",
			runtimeConfigPath: "../clientConfig.ts",
		},
	],
});
