import {
	Badge,
	Box,
	Center,
	DialogBackdrop,
	DialogBody,
	DialogCloseTrigger,
	DialogContent,
	DialogHeader,
	DialogPositioner,
	DialogRoot,
	DialogTitle,
	Stack,
	Text,
	VStack,
} from "@chakra-ui/react";
import { Loader, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { client } from "../../../client/client.gen";

interface SegmentContext {
	src: string;
	tgt: string;
}

interface ExplanationPanelProps {
	segmentId: number;
	workId: number;
	chapterId: number;
	isOpen: boolean;
	onClose: () => void;
}

export function ExplanationPanel({
	segmentId,
	workId,
	chapterId,
	isOpen,
	onClose,
}: ExplanationPanelProps) {
	const { currentSegment, contextLoading, contextError } = useExplanationContext(
		workId,
		chapterId,
		segmentId,
		isOpen,
	);
	const { explanation, isLoading, error, regenerate } = useExplanationStream(
		workId,
		chapterId,
		segmentId,
		isOpen,
	);

	const currentSegmentRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (isOpen && currentSegmentRef.current) {
			currentSegmentRef.current.scrollIntoView({
				behavior: "auto",
				block: "center",
			});
		}
	}, [isOpen, segmentId]);

	if (!isOpen) {
		return null;
	}

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(e) => !e.open && onClose()}
			size="xl"
			scrollBehavior="inside"
		>
			<DialogBackdrop />
			<DialogPositioner>
				<DialogContent maxH="85vh">
					<DialogCloseTrigger />
					<DialogHeader borderBottomWidth="1px" pb={4}>
						<Stack gap={1}>
							<Stack direction="row" align="center" gap={2}>
								<DialogTitle>Translation Breakdown</DialogTitle>
								<Badge colorScheme="purple" variant="subtle" size="sm">
									<Stack direction="row" gap={1} align="center">
										<Sparkles size={10} />
										AI Tutor
									</Stack>
								</Badge>
							</Stack>
						</Stack>
					</DialogHeader>

					<DialogBody py={6}>
						<VStack gap={6} align="stretch">
							{/* Context Section */}
							<VStack gap={0} align="stretch">
								<Text
									fontSize="xs"
									textTransform="uppercase"
									fontWeight="bold"
									color="gray.500"
									letterSpacing="wider"
									mb={2}
								>
									Context
								</Text>

								<Stack gap={3} maxH="300px" overflowY="auto" position="relative" pr={2}>
									{/* Current Segment */}
									<Box
										ref={currentSegmentRef}
										p={4}
										bg="blue.50"
										borderLeftWidth="4px"
										borderLeftColor="blue.500"
										borderRadius="sm"
										shadow="sm"
									>
										<Text
											fontSize="sm"
											fontWeight="bold"
											color="gray.800"
											fontFamily="mono"
											mb={1.5}
										>
											{currentSegment?.src || (contextLoading ? "Loading..." : "")}
										</Text>
										<Text fontSize="md" color="gray.900" fontWeight="medium">
											{currentSegment?.tgt || ""}
										</Text>
									</Box>
									{contextError && (
										<Text fontSize="xs" color="red.500">
											{contextError}
										</Text>
									)}
								</Stack>
							</VStack>

							<Box borderTopWidth="1px" borderColor="gray.100" />

							{/* Explanation Section */}
							<Box>
								<Stack direction="row" justify="space-between" align="center" mb={3}>
									<Text
										fontSize="xs"
										textTransform="uppercase"
										fontWeight="bold"
										color="gray.500"
										letterSpacing="wider"
									>
										Explanation
									</Text>
									{explanation && !isLoading && (
										<Box
											as="button"
											onClick={regenerate}
											color="gray.400"
											_hover={{ color: "blue.500" }}
											transition="color 0.2s"
											title="Regenerate explanation"
										>
											<RefreshCw size={14} />
										</Box>
									)}
								</Stack>

								<Box minH="200px">
									{isLoading && !explanation ? (
										<Center py={8} flexDirection="column" gap={3}>
											<Box
												as={Loader}
												animation="spin 1s linear infinite"
												color="blue.500"
												fontSize="2xl"
											/>
											<Text fontSize="sm" color="gray.500">
												Analyzing translation...
											</Text>
										</Center>
									) : error ? (
										<Box
											p={4}
											bg="red.50"
											color="red.600"
											borderRadius="md"
											fontSize="sm"
										>
											{error}
										</Box>
									) : (
										<Box
											className="markdown-body"
											fontSize="sm"
											lineHeight="1.7"
											css={{
												"& p": { mb: 3 },
												"& ul": { pl: 4, mb: 3 },
												"& li": { mb: 1 },
												"& code": { bg: "gray.100", px: 1, borderRadius: "sm" }
											}}
										>
											<ReactMarkdown>{explanation}</ReactMarkdown>
											{isLoading && (
												<Text as="span" color="blue.400" animation="pulse 1s infinite">
													▋
												</Text>
											)}
										</Box>
									)}
								</Box>
							</Box>
						</VStack>
					</DialogBody>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}

function useExplanationStream(
	workId: number,
	chapterId: number,
	segmentId: number,
	isOpen: boolean,
) {
	const [isLoading, setIsLoading] = useState(false);
	const [explanation, setExplanation] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [shouldRegenerate, setShouldRegenerate] = useState(false);
	const lastSegmentIdRef = useRef<number | null>(null);
	const suppressNextFetchRef = useRef(false);

	const regenerate = useCallback(() => {
		setShouldRegenerate(true);
	}, []);

	useEffect(() => {
		if (!isOpen) {
			setExplanation("");
			setError(null);
			setShouldRegenerate(false);
			lastSegmentIdRef.current = null;
			return;
		}

		if (lastSegmentIdRef.current !== segmentId) {
			setExplanation("");
			setError(null);
			setShouldRegenerate(false);
			lastSegmentIdRef.current = segmentId;
			suppressNextFetchRef.current = false;
		}

		// Don't re-fetch if we're not regenerating and already have an explanation
		if (!shouldRegenerate && explanation) {
			return;
		}

		if (!shouldRegenerate && suppressNextFetchRef.current) {
			suppressNextFetchRef.current = false;
			return;
		}

		setIsLoading(true);
		setError(null);
		setExplanation("");

		let eventSource: EventSource | null = null;
		let abortController: AbortController | null = null;

		async function startStream() {
			try {
				if (shouldRegenerate) {
					// Use fetch API to handle POST request with SSE response
					abortController = new AbortController();
					const response = await fetch(
						`/api/works/${workId}/chapters/${chapterId}/segments/${segmentId}/regenerate-explanation`,
						{
							method: "POST",
							signal: abortController.signal,
						},
					);

					if (!response.ok) {
						throw new Error("Failed to regenerate explanation");
					}

					// Read the SSE response
					const reader = response.body?.getReader();
					const decoder = new TextDecoder();

					if (!reader) {
						throw new Error("No response body");
					}

					let buffer = "";
					while (true) {
						const { done, value } = await reader.read();
						if (done) break;

						buffer += decoder.decode(value, { stream: true });
						const events = buffer.split("\n\n");
						buffer = events.pop() ?? "";

						for (const rawEvent of events) {
							let eventName = "message";
							const dataLines: string[] = [];
							for (const line of rawEvent.split("\n")) {
								if (line.startsWith("event:")) {
									eventName = line.slice(6).trim();
								} else if (line.startsWith("data:")) {
									dataLines.push(line.slice(5).trim());
								}
							}

							if (!dataLines.length) continue;
							let data: { delta?: string; error?: string; explanation?: string } = {};
							try {
								data = JSON.parse(dataLines.join("\n"));
							} catch {
								// Ignore non-JSON payloads
							}

							if (eventName === "explanation-delta") {
								setExplanation((prev) => prev + (data.delta || ""));
							} else if (eventName === "explanation-complete") {
								if (data.explanation) {
									setExplanation(data.explanation);
								}
								setIsLoading(false);
								suppressNextFetchRef.current = true;
							} else if (eventName === "explanation-error") {
								setError(data.error || "Failed to generate explanation");
								setIsLoading(false);
							}
						}
					}

					setShouldRegenerate(false);
				} else {
					// Use EventSource for GET request
					const url = `/api/works/${workId}/chapters/${chapterId}/segments/${segmentId}/explain/stream`;
					eventSource = new EventSource(url);

					eventSource.addEventListener("explanation-delta", (event) => {
						const { delta } = JSON.parse(event.data);
						setExplanation((prev) => prev + (delta || ""));
					});

					eventSource.addEventListener("explanation-complete", () => {
						eventSource?.close();
						setIsLoading(false);
					});

					eventSource.addEventListener("explanation-error", (event) => {
						const { error } = JSON.parse(event.data);
						setError(error || "Failed to generate explanation");
						eventSource?.close();
						setIsLoading(false);
					});

					eventSource.onerror = () => {
						// Only set error if we haven't received any content, 
						// otherwise it might just be a normal close in some browser environments
						// or a network blip after we got the content.
						// But for SSE usually onerror fires on connection loss.
						// We'll check if we have explanations.
						// Actually, safer to just close.
						if (eventSource?.readyState === EventSource.CLOSED) {
							// clean close
						} else {
							// If we already have some explanation, maybe don't error out hard?
							// But for now let's keep it safe.
							// setError("Connection lost while generating explanation");
						}
						eventSource?.close();
						setIsLoading(false);
					};
				}
			} catch (err) {
				if (err instanceof Error && err.name === "AbortError") {
					// Request was aborted, ignore
					return;
				}
				setError(err instanceof Error ? err.message : "Unknown error occurred");
				setIsLoading(false);
				setShouldRegenerate(false);
			}
		}

		startStream();

		return () => {
			if (eventSource) {
				eventSource.close();
			}
			if (abortController) {
				abortController.abort();
			}
		};
	}, [isOpen, segmentId, workId, chapterId, shouldRegenerate]);

	return { explanation, isLoading, error, regenerate };
}

function useExplanationContext(
	workId: number,
	chapterId: number,
	segmentId: number,
	isOpen: boolean,
) {
	const [currentSegment, setCurrentSegment] = useState<SegmentContext | null>(
		null,
	);
	const [contextLoading, setContextLoading] = useState(false);
	const [contextError, setContextError] = useState<string | null>(null);

	useEffect(() => {
		if (!isOpen) {
			setCurrentSegment(null);
			setContextLoading(false);
			setContextError(null);
			return;
		}

		let cancelled = false;
		const controller = new AbortController();

		const loadContext = async () => {
			setContextLoading(true);
			setContextError(null);
			try {
				const response = await client.get({
					url: `/works/${workId}/chapters/${chapterId}/translation`,
					responseType: "json",
					throwOnError: true,
					signal: controller.signal,
				});
				if (cancelled) return;
				const payload = response.data as {
					segments: Array<{
						id: number;
						src: string;
						tgt: string;
					}>;
				};
				const index = payload.segments.findIndex(
					(segment) => segment.id === segmentId,
				);
				if (index === -1) {
					setCurrentSegment(null);
					setContextError("Segment context not found");
					return;
				}
				const toContext = (segment?: { src: string; tgt: string }) =>
					segment ? { src: segment.src || "", tgt: segment.tgt || "" } : null;
				setCurrentSegment(toContext(payload.segments[index]));
			} catch (err) {
				if (!cancelled) {
					setContextError("Failed to load segment context");
				}
			} finally {
				if (!cancelled) {
					setContextLoading(false);
				}
			}
		};

		loadContext();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [isOpen, workId, chapterId, segmentId]);

	return {
		currentSegment,
		contextLoading,
		contextError,
	};
}
