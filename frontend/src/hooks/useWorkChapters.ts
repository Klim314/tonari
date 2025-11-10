import { useEffect, useState } from "react";
import { Works } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PaginatedChaptersResponse } from "../types/works";

interface ChaptersState {
	data: PaginatedChaptersResponse | null;
	loading: boolean;
	error: string | null;
}

const defaultState: ChaptersState = {
	data: null,
	loading: false,
	error: null,
};

export function useWorkChapters(
	workId: number | null | undefined,
	limit: number,
	offset: number,
	refreshToken = 0,
) {
	const [state, setState] = useState<ChaptersState>(defaultState);
	const refreshKey = refreshToken;

	useEffect(() => {
		void refreshKey;
		if (!workId) {
			setState({ ...defaultState });
			return;
		}
		let cancelled = false;
		const controller = new AbortController();

		async function fetchChapters() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await Works.listChaptersForWorkWorksWorkIdChaptersGet({
					path: { work_id: workId },
					query: { limit, offset },
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
					error: getApiErrorMessage(error, "Failed to fetch chapters"),
				});
			}
		}

		fetchChapters();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [workId, limit, offset, refreshKey]);

	return state;
}
