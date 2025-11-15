import axios from "axios";
import { useCallback, useEffect, useState } from "react";
import { Prompts } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PromptDetail } from "../types/prompts";

interface WorkPromptState {
	data: PromptDetail | null;
	loading: boolean;
	error: string | null;
	notAssigned: boolean;
}

const defaultState: WorkPromptState = {
	data: null,
	loading: false,
	error: null,
	notAssigned: false,
};

export function useWorkPromptDetail(workId?: number | null, refreshToken = 0) {
	const [state, setState] = useState<WorkPromptState>(defaultState);
	const [localRefresh, setLocalRefresh] = useState(0);
	const refreshKey = `${refreshToken}:${localRefresh}`;

	const refresh = useCallback(() => {
		setLocalRefresh((value) => value + 1);
	}, []);

	useEffect(() => {
		void refreshKey;
		if (!workId) {
			setState(defaultState);
			return;
		}

		let cancelled = false;
		const controller = new AbortController();

		async function fetchWorkPrompt() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await Prompts.getWorkPromptPromptsWorksWorkIdPromptGet(
					{
						path: { work_id: workId },
						signal: controller.signal,
						throwOnError: true,
					},
				);
				if (cancelled) return;
				setState({
					data: response.data,
					loading: false,
					error: null,
					notAssigned: false,
				});
			} catch (error) {
				if (cancelled || controller.signal.aborted) {
					return;
				}
				if (axios.isAxiosError(error) && error.response?.status === 404) {
					setState({
						data: null,
						loading: false,
						error: null,
						notAssigned: true,
					});
					return;
				}
				setState({
					data: null,
					loading: false,
					error: getApiErrorMessage(
						error,
						"Failed to load the prompt assigned to this work.",
					),
					notAssigned: false,
				});
			}
		}

		fetchWorkPrompt();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [refreshKey, workId]);

	return { ...state, refresh };
}
