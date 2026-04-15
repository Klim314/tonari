import { useCallback, useEffect, useRef, useState } from "react";
import { client } from "../../../../client/client.gen";
import { apiUrl } from "../../../../clientConfig";
import {
	emptyFacets,
	FACET_ORDER,
	type FacetDataMap,
	type FacetsState,
	type FacetType,
} from "./types";

type ArtifactStatus = "idle" | "loading" | "generating" | "complete" | "error";

interface UseExplanationArtifactArgs {
	workId: number;
	chapterId: number;
	segmentId: number;
	spanStart: number;
	spanEnd: number;
	density: "sparse" | "dense";
	enabled: boolean;
}

interface UseExplanationArtifactResult {
	status: ArtifactStatus;
	error: string | null;
	facets: FacetsState;
	regenerate: () => void;
	isRegenerating: boolean;
}

interface ArtifactGetResponse {
	status: string;
	artifact_id?: number | null;
	density?: string | null;
	span_start?: number | null;
	span_end?: number | null;
	facets?: {
		overview?: { status: string; data?: unknown; error?: string | null } | null;
		vocabulary?: {
			status: string;
			data?: unknown;
			error?: string | null;
		} | null;
		grammar?: { status: string; data?: unknown; error?: string | null } | null;
		translation_logic?: {
			status: string;
			data?: unknown;
			error?: string | null;
		} | null;
	} | null;
}

function applyCachedFacets(raw: ArtifactGetResponse["facets"]): FacetsState {
	const next = emptyFacets();
	if (!raw) return next;
	for (const facetType of FACET_ORDER) {
		const entry = raw[facetType];
		if (!entry) continue;
		if (entry.status === "complete" && entry.data) {
			next[facetType] = {
				status: "complete",
				data: entry.data as FacetDataMap[typeof facetType],
				error: null,
			};
		} else if (entry.status === "error") {
			next[facetType] = {
				status: "error",
				data: null,
				error: entry.error ?? "facet generation failed",
			};
		}
	}
	return next;
}

export function useExplanationArtifact({
	workId,
	chapterId,
	segmentId,
	spanStart,
	spanEnd,
	density,
	enabled,
}: UseExplanationArtifactArgs): UseExplanationArtifactResult {
	const [status, setStatus] = useState<ArtifactStatus>("idle");
	const [error, setError] = useState<string | null>(null);
	const [facets, setFacets] = useState<FacetsState>(emptyFacets);
	const [invalidationNonce, setInvalidationNonce] = useState(0);
	const [isRegenerating, setIsRegenerating] = useState(false);

	const eventSourceRef = useRef<EventSource | null>(null);
	const abortRef = useRef<AbortController | null>(null);
	const invalidatedKeyRef = useRef<string | null>(null);
	const streamCompletedRef = useRef(false);
	const requestKey = `${segmentId}:${spanStart}:${spanEnd}:${density}`;

	const cleanup = useCallback(() => {
		eventSourceRef.current?.close();
		eventSourceRef.current = null;
		abortRef.current?.abort();
		abortRef.current = null;
	}, []);

	const regenerate = useCallback(() => {
		invalidatedKeyRef.current = requestKey;
		setInvalidationNonce((n) => n + 1);
	}, [requestKey]);

	useEffect(() => {
		if (!enabled) {
			cleanup();
			setStatus("idle");
			setError(null);
			setFacets(emptyFacets());
			setIsRegenerating(false);
			return;
		}

		const force =
			invalidationNonce > 0 && invalidatedKeyRef.current === requestKey;
		if (force) {
			invalidatedKeyRef.current = null;
		}
		const controller = new AbortController();
		abortRef.current = controller;

		setStatus("loading");
		setError(null);
		setFacets(emptyFacets());
		setIsRegenerating(force);

		const base = `/works/${workId}/chapters/${chapterId}/segments/${segmentId}/sentences/explanation`;
		const query = `span_start=${spanStart}&span_end=${spanEnd}&density=${density}`;

		const openStream = () => {
			if (controller.signal.aborted) return;
			const url = apiUrl(`${base}/stream?${query}`);
			const es = new EventSource(url);
			eventSourceRef.current = es;
			streamCompletedRef.current = false;
			setStatus("generating");

			es.addEventListener("explanation-facet-complete", (ev) => {
				try {
					const msg = JSON.parse((ev as MessageEvent).data) as {
						facet_type: FacetType;
						payload: unknown;
					};
					setFacets((prev) => ({
						...prev,
						[msg.facet_type]: {
							status: "complete",
							data: msg.payload as FacetDataMap[typeof msg.facet_type],
							error: null,
						},
					}));
				} catch {
					// ignore malformed event
				}
			});

			es.addEventListener("explanation-error", (ev) => {
				try {
					const msg = JSON.parse((ev as MessageEvent).data) as {
						facet_type?: FacetType;
						message?: string;
					};
					if (msg.facet_type) {
						setFacets((prev) => ({
							...prev,
							[msg.facet_type as FacetType]: {
								status: "error",
								data: null,
								error: msg.message ?? "facet generation failed",
							},
						}));
					} else {
						setError(msg.message ?? "explanation generation failed");
					}
				} catch {
					// ignore
				}
			});

			es.addEventListener("explanation-complete", (ev) => {
				try {
					const msg = JSON.parse((ev as MessageEvent).data) as {
						status: string;
					};
					setStatus(msg.status === "error" ? "error" : "complete");
				} catch {
					setStatus("complete");
				}
				streamCompletedRef.current = true;
				setIsRegenerating(false);
				es.close();
				eventSourceRef.current = null;
			});

			es.onerror = () => {
				// SSE onerror also fires during transient reconnect attempts
				// (readyState === CONNECTING). Only treat a terminal close before
				// explanation-complete as a real error.
				if (streamCompletedRef.current) return;
				if (es.readyState === EventSource.CONNECTING) return;
				if (es.readyState !== EventSource.CLOSED) return;
				eventSourceRef.current = null;
				setStatus((prev) => (prev === "complete" ? prev : "error"));
				setError((prev) => prev ?? "connection lost");
				setIsRegenerating(false);
			};
		};

		const run = async () => {
			try {
				if (!force) {
					const getResp = await client.get<ArtifactGetResponse>({
						url: `${base}?${query}`,
						responseType: "json",
						signal: controller.signal,
						throwOnError: true,
					});
					if (controller.signal.aborted) return;
					const data = getResp.data as ArtifactGetResponse;
					// Hydrate whatever facets are already persisted so partial
					// progress renders immediately; the stream will fill the rest.
					if (data.facets) {
						setFacets(applyCachedFacets(data.facets));
					}
					if (data.status === "complete") {
						setStatus("complete");
						return;
					}
				}

				await client.post({
					url: base,
					body: {
						span_start: spanStart,
						span_end: spanEnd,
						density,
						force,
					},
					responseType: "json",
					signal: controller.signal,
					throwOnError: true,
				});
				if (controller.signal.aborted) return;
				openStream();
			} catch (err) {
				if (controller.signal.aborted) return;
				if (err instanceof Error && err.name === "AbortError") return;
				setStatus("error");
				setError(
					err instanceof Error ? err.message : "failed to load explanation",
				);
				setIsRegenerating(false);
			}
		};

		void run();

		return () => {
			controller.abort();
			cleanup();
		};
	}, [
		enabled,
		workId,
		chapterId,
		segmentId,
		spanStart,
		spanEnd,
		density,
		requestKey,
		invalidationNonce,
		cleanup,
	]);

	return { status, error, facets, regenerate, isRegenerating };
}
