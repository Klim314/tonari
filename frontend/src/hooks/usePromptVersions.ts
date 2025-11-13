import { useEffect, useState } from "react";
import { Prompts } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PaginatedPromptVersionsResponse } from "../types/prompts";

interface PromptVersionsState {
	data: PaginatedPromptVersionsResponse | null;
	loading: boolean;
	error: string | null;
}

const defaultState: PromptVersionsState = {
	data: null,
	loading: false,
	error: null,
};

export function usePromptVersions(promptId: number | null, refreshToken = 0) {
	const [state, setState] = useState<PromptVersionsState>(defaultState);
	const refreshKey = refreshToken;

	useEffect(() => {
		void refreshKey;
		if (!promptId) {
			setState(defaultState);
			return;
		}

		let cancelled = false;
		const controller = new AbortController();

		async function fetchVersions() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await Prompts.listPromptVersionsPromptsPromptIdVersionsGet({
					path: { prompt_id: promptId },
					query: {
						limit: 50,
						offset: 0,
					},
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
					error: getApiErrorMessage(error, "Failed to fetch prompt versions"),
				});
			}
		}

		fetchVersions();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [promptId, refreshKey]);

	return state;
}
