import { useEffect, useState } from "react";
import { Works } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PaginatedWorksResponse } from "../types/works";

interface WorksState {
	data: PaginatedWorksResponse | null;
	loading: boolean;
	error: string | null;
}

const defaultState: WorksState = {
	data: null,
	loading: false,
	error: null,
};

export function useWorks(searchQuery: string, refreshToken = 0) {
	const [state, setState] = useState<WorksState>({
		...defaultState,
		loading: true,
	});
	const refreshKey = refreshToken;

	useEffect(() => {
		void refreshKey;
		let cancelled = false;
		const controller = new AbortController();

		async function fetchWorks() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const trimmedQuery = searchQuery.trim();
				const query: NonNullable<
					Parameters<typeof Works.searchWorksWorksGet>[0]
				>["query"] = {
					limit: 50,
					offset: 0,
				};
				if (trimmedQuery) {
					query.q = trimmedQuery;
				}

				const response = await Works.searchWorksWorksGet({
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
					error: getApiErrorMessage(error, "Failed to fetch works"),
				});
			}
		}

		fetchWorks();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [searchQuery, refreshKey]);

	return state;
}
