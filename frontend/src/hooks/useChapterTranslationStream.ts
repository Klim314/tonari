import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { client } from "../client/client.gen";

export type TranslationStreamStatus =
	| "idle"
	| "connecting"
	| "running"
	| "completed"
	| "error";

interface SegmentState {
	segmentId: number;
	orderIndex: number;
	start: number;
	end: number;
	src: string;
	text: string;
	status: "pending" | "running" | "completed";
}

interface UseChapterTranslationStreamOptions {
	workId?: number | null;
	chapterId?: number | null;
	autoStart?: boolean;
}

interface TranslationStreamHook {
	status: TranslationStreamStatus;
	error: string | null;
	segments: SegmentState[];
	isStreaming: boolean;
	start: () => void;
	pause: () => void;
	reset: () => void;
	isResetting: boolean;
	regenerate: () => Promise<boolean>;
	retranslateSegment: (segmentId: number) => void;
}

interface ChapterTranslationStateResponse {
	chapter_translation_id: number;
	status: string;
	segments: Array<{
		id: number;
		start: number;
		end: number;
		order_index: number;
		src: string;
		tgt: string;
		flags?: string[];
	}>;
}

function sanitizeBaseUrl(baseURL?: string): string {
	if (!baseURL) {
		return "";
	}
	return baseURL.endsWith("/") ? baseURL.slice(0, -1) : baseURL;
}

function buildStreamUrl(workId: number, chapterId: number): string {
	return buildChapterActionUrl(workId, chapterId, "/translate/stream");
}

function buildChapterActionUrl(
	workId: number,
	chapterId: number,
	actionPath: string,
): string {
	const baseURL = sanitizeBaseUrl(client.getConfig().baseURL || "/api");
	const path = `/works/${workId}/chapters/${chapterId}${actionPath}`;
	if (!baseURL) {
		return path;
	}
	return `${baseURL}${path}`;
}

function parseEventData<T = Record<string, unknown>>(
	event: MessageEvent<string>,
): T | null {
	try {
		return JSON.parse(event.data) as T;
	} catch (error) {
		console.error("Failed to parse SSE payload", error);
		return null;
	}
}

function normalizeStatus(value?: string | null): TranslationStreamStatus {
	switch (value) {
		case "running":
			return "running";
		case "completed":
			return "completed";
		case "connecting":
			return "connecting";
		case "error":
			return "error";
		default:
			return "idle";
	}
}

export function useChapterTranslationStream({
	workId,
	chapterId,
	autoStart = false,
}: UseChapterTranslationStreamOptions): TranslationStreamHook {
	const [status, setStatus] = useState<TranslationStreamStatus>("idle");
	const [error, setError] = useState<string | null>(null);
	const [segmentsMap, setSegmentsMap] = useState<Record<number, SegmentState>>(
		{},
	);
	const [isResetting, setIsResetting] = useState(false);
	const eventSourceRef = useRef<EventSource | null>(null);

	const closeStream = useCallback((nextStatus?: TranslationStreamStatus) => {
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
			eventSourceRef.current = null;
		}
		if (nextStatus) {
			setStatus(nextStatus);
		} else {
			setStatus((prev) =>
				prev === "running" || prev === "connecting" ? "idle" : prev,
			);
		}
	}, []);

	const reset = useCallback(() => {
		closeStream("idle");
		setSegmentsMap({});
		setError(null);
	}, [closeStream]);

	const applyPayload = useCallback(
		(payload: ChapterTranslationStateResponse) => {
			setStatus(normalizeStatus(payload.status));
			const mapped: Record<number, SegmentState> = {};
			for (const segment of payload.segments) {
				const isWhitespace = segment.flags?.includes("whitespace");
				mapped[segment.id] = {
					segmentId: segment.id,
					orderIndex: segment.order_index,
					start: segment.start,
					end: segment.end,
					src: segment.src,
					text: segment.tgt ?? "",
					status: segment.tgt || isWhitespace ? "completed" : "pending",
				};
			}
			setSegmentsMap(mapped);
		},
		[],
	);

	const handleSegmentStart = useCallback((event: MessageEvent<string>) => {
		const payload = parseEventData<{
			segment_id: number;
			order_index: number;
			start: number;
			end: number;
			src: string;
		}>(event);
		if (!payload) return;

		setSegmentsMap((prev) => {
			const next = { ...prev };
			const existing = next[payload.segment_id];
			next[payload.segment_id] = {
				segmentId: payload.segment_id,
				orderIndex: payload.order_index,
				start: payload.start,
				end: payload.end,
				src: payload.src,
				text: existing?.text ?? "",
				status: "running",
			};
			return next;
		});
	}, []);

	const handleSegmentDelta = useCallback((event: MessageEvent<string>) => {
		const payload = parseEventData<{
			segment_id: number;
			delta: string;
		}>(event);
		if (!payload) return;
		setSegmentsMap((prev) => {
			const existing = prev[payload.segment_id];
			if (!existing) return prev;
			return {
				...prev,
				[payload.segment_id]: {
					...existing,
					text: existing.text + (payload.delta ?? ""),
					status: "running",
				},
			};
		});
	}, []);

	const handleSegmentComplete = useCallback((event: MessageEvent<string>) => {
		const payload = parseEventData<{
			segment_id: number;
			text: string;
		}>(event);
		if (!payload) return;
		setSegmentsMap((prev) => {
			const existing = prev[payload.segment_id];
			if (!existing) return prev;
			return {
				...prev,
				[payload.segment_id]: {
					...existing,
					text: payload.text ?? existing.text,
					status: "completed",
				},
			};
		});
	}, []);

	const start = useCallback(() => {
		if (!workId || !chapterId) {
			setError("Missing work or chapter identifier");
			return;
		}
		if (eventSourceRef.current) {
			return;
		}
		setStatus("connecting");
		setError(null);

		const url = buildStreamUrl(workId, chapterId);
		const source = new EventSource(url);
		eventSourceRef.current = source;

		source.addEventListener("translation-status", (event) => {
			const payload = parseEventData<{ status: string }>(
				event as MessageEvent<string>,
			);
			if (!payload) return;
			setStatus(normalizeStatus(payload.status));
		});
		source.addEventListener(
			"segment-start",
			handleSegmentStart as EventListener,
		);
		source.addEventListener(
			"segment-delta",
			handleSegmentDelta as EventListener,
		);
		source.addEventListener(
			"segment-complete",
			handleSegmentComplete as EventListener,
		);
		source.addEventListener("translation-error", (event) => {
			const payload = parseEventData<{ error?: string }>(
				event as MessageEvent<string>,
			);
			setError(payload?.error ?? "Translation run failed");
			setStatus("error");
			closeStream("error");
		});
		source.addEventListener("translation-complete", () => {
			setStatus("completed");
			closeStream("completed");
		});
		source.onerror = () => {
			setError("Translation stream disconnected");
			closeStream("error");
		};
	}, [
		chapterId,
		closeStream,
		handleSegmentComplete,
		handleSegmentDelta,
		handleSegmentStart,
		workId,
	]);

	const pause = useCallback(() => {
		closeStream("idle");
	}, [closeStream]);

	useEffect(() => {
		return () => {
			closeStream();
		};
	}, [closeStream]);

	useEffect(() => {
		if (!workId || !chapterId) {
			reset();
			return;
		}
		let cancelled = false;
		const hydrate = async () => {
			reset();
			try {
				const response = await client.get({
					url: `/works/${workId}/chapters/${chapterId}/translation`,
					responseType: "json",
					throwOnError: true,
				});
				if (cancelled) return;
				const payload = response.data as ChapterTranslationStateResponse;
				applyPayload(payload);
				setError(null);
			} catch (err) {
				if (!cancelled) {
					setSegmentsMap({});
					setError("Failed to load saved translation");
				}
			}
		};
		hydrate();
		return () => {
			cancelled = true;
		};
	}, [chapterId, workId, reset, applyPayload]);

	const regenerate = useCallback(async () => {
		if (!workId || !chapterId) {
			setError("Missing work or chapter identifier");
			return false;
		}
		reset();
		setIsResetting(true);
		setError(null);
		try {
			const response = await client.delete({
				url: `/works/${workId}/chapters/${chapterId}/translation`,
				responseType: "json",
				throwOnError: true,
			});
			const payload = response.data as ChapterTranslationStateResponse;
			applyPayload(payload);
			return true;
		} catch (err) {
			setError("Failed to reset translation");
			return false;
		} finally {
			setIsResetting(false);
		}
	}, [applyPayload, chapterId, workId, reset]);

	useEffect(() => {
		if (autoStart) {
			start();
		}
	}, [autoStart, start]);

	const segments = useMemo(() => {
		return Object.values(segmentsMap).sort(
			(a, b) => a.orderIndex - b.orderIndex,
		);
	}, [segmentsMap]);

	const retranslateSegment = useCallback(
		(segmentId: number) => {
			if (!workId || !chapterId) {
				setError("Missing work or chapter identifier");
				return;
			}
			if (eventSourceRef.current) {
				eventSourceRef.current.close();
				eventSourceRef.current = null;
			}

			const url = buildChapterActionUrl(
				workId,
				chapterId,
				`/segments/${segmentId}/retranslate/stream`,
			);
			const source = new EventSource(url);
			eventSourceRef.current = source;

			source.addEventListener(
				"segment-start",
				handleSegmentStart as EventListener,
			);
			source.addEventListener(
				"segment-delta",
				handleSegmentDelta as EventListener,
			);
			source.addEventListener(
				"segment-complete",
				handleSegmentComplete as EventListener,
			);
			source.addEventListener("translation-error", (event) => {
				const payload = parseEventData<{ error?: string }>(
					event as MessageEvent<string>,
				);
				setError(payload?.error ?? "Segment retranslation failed");
				closeStream("error");
			});
			source.onerror = () => {
				setError("Retranslation stream disconnected");
				closeStream("error");
			};
		},
		[chapterId, closeStream, handleSegmentComplete, handleSegmentDelta, handleSegmentStart, workId],
	);

	return {
		status,
		error,
		segments,
		isStreaming: status === "connecting" || status === "running",
		start,
		pause,
		reset,
		isResetting,
		regenerate,
		retranslateSegment,
	};
}
