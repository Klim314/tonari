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
	regenerateFacet: (facetType: FacetType) => void;
	isRegenerating: boolean;
	regeneratingFacet: FacetType | null;
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
			switch (facetType) {
				case "overview":
					next.overview = {
						status: "complete",
						data: entry.data as FacetDataMap["overview"],
						error: null,
					};
					break;
				case "vocabulary":
					next.vocabulary = {
						status: "complete",
						data: entry.data as FacetDataMap["vocabulary"],
						error: null,
					};
					break;
				case "grammar":
					next.grammar = {
						status: "complete",
						data: entry.data as FacetDataMap["grammar"],
						error: null,
					};
					break;
				case "translation_logic":
					next.translation_logic = {
						status: "complete",
						data: entry.data as FacetDataMap["translation_logic"],
						error: null,
					};
					break;
			}
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
	const [regeneratingFacet, setRegeneratingFacet] = useState<FacetType | null>(
		null,
	);

	const eventSourceRef = useRef<EventSource | null>(null);
	const abortRef = useRef<AbortController | null>(null);
	const invalidatedKeyRef = useRef<string | null>(null);
	const streamCompletedRef = useRef(false);
	const facetRegenRef = useRef<EventSource | null>(null);
	const facetRegenAbortRef = useRef<AbortController | null>(null);
	const requestKey = `${segmentId}:${spanStart}:${spanEnd}:${density}`;

	const cleanup = useCallback(() => {
		eventSourceRef.current?.close();
		eventSourceRef.current = null;
		abortRef.current?.abort();
		abortRef.current = null;
	}, []);

	const cleanupFacetRegen = useCallback(() => {
		facetRegenRef.current?.close();
		facetRegenRef.current = null;
		facetRegenAbortRef.current?.abort();
		facetRegenAbortRef.current = null;
	}, []);

	const regenerate = useCallback(() => {
		cleanupFacetRegen();
		setRegeneratingFacet(null);
		invalidatedKeyRef.current = requestKey;
		setInvalidationNonce((n) => n + 1);
	}, [requestKey, cleanupFacetRegen]);

	const base = `/works/${workId}/chapters/${chapterId}/segments/${segmentId}/sentences/explanation`;
	const query = `span_start=${spanStart}&span_end=${spanEnd}&density=${density}`;

	const regenerateFacet = useCallback(
		(facetType: FacetType) => {
			// Clean up any prior facet regen
			cleanupFacetRegen();

			setRegeneratingFacet(facetType);
			// Reset only this facet to pending
			setFacets((prev) => ({
				...prev,
				[facetType]: { status: "generating", data: null, error: null },
			}));

			const controller = new AbortController();
			facetRegenAbortRef.current = controller;

			const run = async () => {
				try {
					// POST with force + facet_types to reset only this facet
					await client.post({
						url: base,
						body: {
							span_start: spanStart,
							span_end: spanEnd,
							density,
							force: true,
							facet_types: [facetType],
						},
						responseType: "json",
						signal: controller.signal,
						throwOnError: true,
					});
					if (controller.signal.aborted) return;

					// Open SSE stream — the backend will replay completed facets
					// and only generate the one we reset
					const url = apiUrl(`${base}/stream?${query}`);
					const es = new EventSource(url);
					facetRegenRef.current = es;

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
							}
						} catch {
							// ignore
						}
					});

					es.addEventListener("explanation-complete", () => {
						setRegeneratingFacet(null);
						es.close();
						facetRegenRef.current = null;
					});

					es.onerror = () => {
						if (es.readyState === EventSource.CONNECTING) return;
						if (es.readyState !== EventSource.CLOSED) return;
						facetRegenRef.current = null;
						setRegeneratingFacet(null);
						setFacets((prev) => ({
							...prev,
							[facetType]: {
								status: "error",
								data: null,
								error: "connection lost",
							},
						}));
					};
				} catch (err) {
					if (controller.signal.aborted) return;
					if (err instanceof Error && err.name === "AbortError") return;
					setRegeneratingFacet(null);
					setFacets((prev) => ({
						...prev,
						[facetType]: {
							status: "error",
							data: null,
							error:
								err instanceof Error
									? err.message
									: "failed to regenerate facet",
						},
					}));
				}
			};

			void run();
		},
		[base, query, spanStart, spanEnd, density, cleanupFacetRegen],
	);

	useEffect(() => {
		if (!enabled) {
			cleanup();
			cleanupFacetRegen();
			setStatus("idle");
			setError(null);
			setFacets(emptyFacets());
			setIsRegenerating(false);
			setRegeneratingFacet(null);
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
					const getResp = await client.get<ArtifactGetResponse, unknown, true>({
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
		spanStart,
		spanEnd,
		density,
		requestKey,
		invalidationNonce,
		cleanup,
		cleanupFacetRegen,
		base,
		query,
	]);

	return {
		status,
		error,
		facets,
		regenerate,
		regenerateFacet,
		isRegenerating,
		regeneratingFacet,
	};
}
