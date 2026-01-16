import { useEffect, useState } from "react";

export type ScrapeStatus =
	| "pending"
	| "running"
	| "completed"
	| "failed"
	| "idle";

interface ScrapeState {
	status: ScrapeStatus;
	progress: number;
	total: number;
	error?: string;
}

export function useScrapeStatus(workId: number, onChapterFound?: () => void) {
	const [scrapeState, setScrapeState] = useState<ScrapeState>({
		status: "idle",
		progress: 0,
		total: 0,
	});

	useEffect(() => {
		const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";
		const url = `${baseUrl}/works/${workId}/scrape-status`;
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
				}));
			} catch (e) {
				console.error("Failed to parse job-status", e);
			}
		});

		eventSource.addEventListener("chapter-found", () => {
			onChapterFound?.();
		});

		eventSource.onerror = () => {
			// If connection fails, we might want to retry or just log
			// EventSource auto-retries by default usually
		};

		return () => {
			eventSource.close();
		};
	}, [workId, onChapterFound]);

	return scrapeState;
}
