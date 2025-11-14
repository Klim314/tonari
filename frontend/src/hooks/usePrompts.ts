import { useEffect, useRef, useState } from "react";
import { Prompts } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PaginatedPromptsResponse } from "../types/prompts";

interface PromptsState {
	data: PaginatedPromptsResponse | null;
	loading: boolean;
	error: string | null;
}

const defaultState: PromptsState = {
	data: null,
	loading: false,
	error: null,
};

const SEARCH_DEBOUNCE_MS = 300;

export function usePrompts(searchQuery: string, refreshToken = 0) {
	const [state, setState] = useState<PromptsState>(defaultState);
	const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const refreshKey = refreshToken;

	useEffect(() => {
		void refreshKey;
		let cancelled = false;
		const controller = new AbortController();

		async function fetchPrompts() {
			try {
				const trimmedQuery = searchQuery.trim();
				const query: NonNullable<
					Parameters<typeof Prompts.listPromptsPromptsGet>[0]
				>["query"] = {
					limit: 50,
					offset: 0,
				};
				if (trimmedQuery) {
					query.q = trimmedQuery;
				}

				const response = await Prompts.listPromptsPromptsGet({
					query,
					signal: controller.signal,
					throwOnError: true,
				});

				if (!cancelled) {
					setState({
						data: response.data,
						loading: false,
						error: null,
					});
				}
			} catch (error) {
				if (cancelled || controller.signal.aborted) {
					return;
				}
				setState({
					data: null,
					loading: false,
					error: getApiErrorMessage(error, "Failed to fetch prompts"),
				});
			}
		}

		// Set loading state immediately
		setState((prev) => ({ ...prev, loading: true, error: null }));

		// Debounce the actual fetch
		if (debounceTimerRef.current) {
			clearTimeout(debounceTimerRef.current);
		}

		debounceTimerRef.current = setTimeout(() => {
			fetchPrompts();
		}, SEARCH_DEBOUNCE_MS);

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [searchQuery, refreshKey]);

	return state;
}
