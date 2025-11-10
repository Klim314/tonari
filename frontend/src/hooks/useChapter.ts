import { useEffect, useState } from "react";
import { apiClient } from "../lib/api";
import type { ChapterDetail } from "../types/works";

interface ChapterState {
	data: ChapterDetail | null;
	loading: boolean;
	error: string | null;
}

const defaultState: ChapterState = {
	data: null,
	loading: false,
	error: null,
};

export function useChapter(
	workId: number | null | undefined,
	chapterId: number | null | undefined,
	refreshToken = 0,
) {
	const [state, setState] = useState<ChapterState>(defaultState);

	useEffect(() => {
		if (!workId || !chapterId) {
			setState({ ...defaultState });
			return;
		}
		let cancelled = false;
		const controller = new AbortController();

		async function fetchChapter() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await apiClient.get<ChapterDetail>(
					`/works/${workId}/chapters/${chapterId}`,
					{ signal: controller.signal },
				);
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
					error:
						error instanceof Error ? error.message : "Failed to fetch chapter",
				});
			}
		}

		fetchChapter();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [workId, chapterId, refreshToken]);

	return state;
}
