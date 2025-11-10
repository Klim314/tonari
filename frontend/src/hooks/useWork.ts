import { useEffect, useState } from "react";
import { Works } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { Work } from "../types/works";

interface WorkState {
	data: Work | null;
	loading: boolean;
	error: string | null;
}

const defaultState: WorkState = {
	data: null,
	loading: false,
	error: null,
};

export function useWork(workId?: number | null, refreshToken = 0) {
	const [state, setState] = useState<WorkState>(defaultState);
	const refreshKey = refreshToken;

	useEffect(() => {
		void refreshKey;
		if (!workId) {
			setState({ ...defaultState });
			return;
		}
		let cancelled = false;
		const controller = new AbortController();

		async function fetchWork() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await Works.getWorkWorksWorkIdGet({
					path: { work_id: workId },
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
					error: getApiErrorMessage(error, "Failed to fetch work"),
				});
			}
		}

		fetchWork();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [workId, refreshKey]);

	return state;
}
