import axios from "axios";

type DetailShape =
	| string
	| null
	| undefined
	| Array<{ msg?: string } | string>
	| { msg?: string };

type ValidationErrorResponse = {
	detail?: DetailShape;
	errors?: Array<{ field?: string; message?: string; type?: string }>;
};

function extractDetail(detail: DetailShape): string | null {
	if (!detail) {
		return null;
	}
	if (typeof detail === "string") {
		return detail.trim() || null;
	}
	if (Array.isArray(detail)) {
		for (const entry of detail) {
			const message =
				typeof entry === "string"
					? entry
					: typeof entry?.msg === "string"
						? entry.msg
						: null;
			const trimmedMessage = message?.trim();
			if (trimmedMessage) {
				return trimmedMessage;
			}
		}
		return null;
	}
	if (typeof detail === "object" && typeof detail.msg === "string") {
		return detail.msg.trim() || null;
	}
	return null;
}

export function getApiErrorMessage(error: unknown, fallback: string) {
	if (axios.isAxiosError(error)) {
		const responseData = error.response?.data as
			| ValidationErrorResponse
			| undefined;

		// Check for structured validation errors array
		if (responseData?.errors && Array.isArray(responseData.errors)) {
			const fieldErrors = responseData.errors
				.map((e) => {
					if (e.field && e.field !== "unknown") {
						return `${e.field}: ${e.message}`;
					}
					return e.message;
				})
				.filter(Boolean);
			if (fieldErrors.length > 0) {
				return fieldErrors.join("\n");
			}
		}

		// Fall back to detail field
		const detail = extractDetail(responseData?.detail);
		if (detail) {
			return detail;
		}

		if (error.response?.statusText) {
			return error.response.statusText;
		}
		if (error.message) {
			return error.message;
		}
	}

	if (error instanceof Error && error.message) {
		return error.message;
	}

	return fallback;
}
