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
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

interface SegmentContext {
	src: string;
	tgt: string;
}

interface ExplanationPanelProps {
	segmentId: number;
	workId: number;
	chapterId: number;
	currentSegment: SegmentContext;
	precedingSegment?: SegmentContext;
	followingSegment?: SegmentContext;
	isOpen: boolean;
	onClose: () => void;
}

export function ExplanationPanel({
	segmentId,
	workId,
	chapterId,
	currentSegment,
	precedingSegment,
	followingSegment,
	isOpen,
	onClose,
}: ExplanationPanelProps) {
	const { explanation, isLoading, error, regenerate } = useExplanationStream(
		workId,
		chapterId,
		segmentId,
		isOpen,
	);

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

								<Stack gap={3}>
									{/* Previous Segment */}
									{precedingSegment && (
										<Box opacity={0.6}>
											<Text fontSize="xs" color="gray.500" fontFamily="mono" mb={0.5}>
												{precedingSegment.src}
											</Text>
											<Text fontSize="sm" color="gray.500">
												{precedingSegment.tgt}
											</Text>
										</Box>
									)}

									{/* Current Segment */}
									<Box
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
											{currentSegment.src}
										</Text>
										<Text fontSize="md" color="gray.900" fontWeight="medium">
											{currentSegment.tgt}
										</Text>
									</Box>

									{/* Next Segment */}
									{followingSegment && (
										<Box opacity={0.6}>
											<Text fontSize="xs" color="gray.500" fontFamily="mono" mb={0.5}>
												{followingSegment.src}
											</Text>
											<Text fontSize="sm" color="gray.500">
												{followingSegment.tgt}
											</Text>
										</Box>
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

	const regenerate = useCallback(() => {
		setShouldRegenerate(true);
	}, []);

	useEffect(() => {
		if (!isOpen) {
			setExplanation("");
			setError(null);
			setShouldRegenerate(false);
			return;
		}

		// Don't re-fetch if we're not regenerating and already have an explanation
		if (!shouldRegenerate && explanation) {
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

					while (true) {
						const { done, value } = await reader.read();
						if (done) break;

						const chunk = decoder.decode(value, { stream: true });
						const lines = chunk.split("\n");

						for (const line of lines) {
							if (line.startsWith("data: ")) {
								const data = JSON.parse(line.slice(6));

								if (line.includes("explanation-delta")) {
									setExplanation((prev) => prev + (data.delta || ""));
								} else if (line.includes("explanation-complete")) {
									setIsLoading(false);
								} else if (line.includes("explanation-error")) {
									setError(data.error || "Failed to generate explanation");
									setIsLoading(false);
								}
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
