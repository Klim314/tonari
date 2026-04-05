import { useEffect, useEffectEvent, useState } from "react";
import { apiUrl } from "../clientConfig";

export type ScrapeStatus =
	| "pending"
	| "running"
	| "completed"
	| "partial"
	| "failed"
	| "idle";

export interface ChapterError {
	chapter: number;
	reason: string;
}

interface ScrapeState {
	status: ScrapeStatus;
	progress: number;
	total: number;
	error?: string;
	chapterErrors: ChapterError[];
	created: number;
	updated: number;
	skipped: number;
	failed: number;
}

export function useScrapeStatus(workId: number, onChapterFound?: () => void) {
	const [scrapeState, setScrapeState] = useState<ScrapeState>({
		status: "idle",
		progress: 0,
		total: 0,
		chapterErrors: [],
		created: 0,
		updated: 0,
		skipped: 0,
		failed: 0,
	});
	const handleChapterFound = useEffectEvent(() => {
		onChapterFound?.();
	});

	// biome-ignore lint/correctness/useExhaustiveDependencies: handleChapterFound is a useEffectEvent — intentionally excluded from deps
	useEffect(() => {
		if (workId <= 0) {
			return;
		}

		const url = apiUrl(`/works/${workId}/scrape-status`);
		const eventSource = new EventSource(url);

		eventSource.addEventListener("job-status", (event) => {
			try {
				const data = JSON.parse(event.data);
				setScrapeState((prev) => ({
					...prev,
					status: data.status,
					progress: data.progress ?? prev.progress,
					total: data.total ?? prev.total,
					error: data.error,
					chapterErrors: data.errors ?? prev.chapterErrors,
					created: data.created ?? prev.created,
					updated: data.updated ?? prev.updated,
					skipped: data.skipped ?? prev.skipped,
					failed: data.failed ?? prev.failed,
				}));
			} catch (e) {
				console.error("Failed to parse job-status", e);
			}
		});

		eventSource.addEventListener("chapter-error", (event) => {
			try {
				const data = JSON.parse(event.data) as ChapterError;
				setScrapeState((prev) => ({
					...prev,
					chapterErrors: [...prev.chapterErrors, data],
					failed: prev.failed + 1,
				}));
			} catch (e) {
				console.error("Failed to parse chapter-error", e);
			}
		});

		eventSource.addEventListener("chapter-found", () => {
			handleChapterFound();
		});

		eventSource.onerror = () => {
			// EventSource auto-retries by default
		};

		return () => {
			eventSource.close();
		};
	}, [workId]);

	return scrapeState;
}
