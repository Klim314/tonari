import { useEffect, useState } from "react";
import { Prompts } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PromptDetail } from "../types/prompts";

interface PromptState {
	data: PromptDetail | null;
	loading: boolean;
	error: string | null;
}

const defaultState: PromptState = {
	data: null,
	loading: false,
	error: null,
};

export function usePrompt(promptId: number | null, refreshToken = 0) {
	const [state, setState] = useState<PromptState>(defaultState);
	const refreshKey = refreshToken;

	useEffect(() => {
		void refreshKey;
		if (!promptId) {
			setState(defaultState);
			return;
		}

		let cancelled = false;
		const controller = new AbortController();

		async function fetchPrompt() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await Prompts.getPromptPromptsPromptIdGet({
					path: { prompt_id: promptId },
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
					error: getApiErrorMessage(error, "Failed to fetch prompt"),
				});
			}
		}

		fetchPrompt();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [promptId, refreshKey]);

	return state;
}
