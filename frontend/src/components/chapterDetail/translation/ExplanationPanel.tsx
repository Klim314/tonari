import {
	Badge,
	Box,
	Center,
	CloseButton,
	Heading,
	IconButton,
	Menu,
	Portal,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Loader, Menu as MenuIcon, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
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

	const [panelWidth, setPanelWidth] = useState(600);
	const isDragging = useRef(false);
	const startX = useRef(0);
	const startWidth = useRef(0);

	const startResizing = useCallback(
		(e: React.MouseEvent) => {
			isDragging.current = true;
			startX.current = e.clientX;
			startWidth.current = panelWidth;
			document.body.style.cursor = "ew-resize";
			document.body.style.userSelect = "none";
		},
		[panelWidth],
	);

	const stopResizing = useCallback(() => {
		isDragging.current = false;
		document.body.style.cursor = "";
		document.body.style.userSelect = "";
	}, []);

	const resize = useCallback((e: MouseEvent) => {
		if (!isDragging.current) return;
		const delta = startX.current - e.clientX;
		const newWidth = Math.min(Math.max(startWidth.current + delta, 400), 1200);
		setPanelWidth(newWidth);
	}, []);

	useEffect(() => {
		window.addEventListener("mousemove", resize);
		window.addEventListener("mouseup", stopResizing);
		return () => {
			window.removeEventListener("mousemove", resize);
			window.removeEventListener("mouseup", stopResizing);
		};
	}, [resize, stopResizing]);

	if (!isOpen) {
		return null;
	}

	return (
		<Box
			position="fixed"
			right={0}
			top={0}
			bottom={0}
			width={`${panelWidth}px`}
			bg="white"
			borderLeftWidth="1px"
			borderLeftColor="gray.200"
			boxShadow="lg"
			zIndex={1000}
			display="flex"
			flexDirection="column"
		>
			{/* Resize Handle */}
			<Box
				position="absolute"
				left="-5px"
				top={0}
				bottom={0}
				width="10px"
				cursor="ew-resize"
				zIndex={1001}
				onMouseDown={startResizing}
				_hover={{ bg: "blue.100" }}
				transition="background 0.2s"
				bg="gray.200"
			/>

			{/* Header */}
			<Stack
				p={4}
				borderBottomWidth="1px"
				borderBottomColor="gray.200"
				gap={2}
				flexShrink={0}
			>
				<Box display="flex" justifyContent="space-between" alignItems="center">
					<Box display="flex" alignItems="center" gap={2}>
						<Heading size="md">Translation Explanation</Heading>
						<Badge
							colorScheme="purple"
							variant="subtle"
							display="flex"
							alignItems="center"
							gap={1}
						>
							<Sparkles size={12} />
							AI
						</Badge>
					</Box>
					<Box display="flex" alignItems="center" gap={2}>
						<Menu.Root>
							<Menu.Trigger asChild>
								<IconButton variant="ghost" size="sm" aria-label="Options">
									<MenuIcon size={16} />
								</IconButton>
							</Menu.Trigger>
							<Portal>
								<Menu.Positioner>
									<Menu.Content>
										<Menu.Item
											value="regenerate"
											onClick={regenerate}
											disabled={!explanation || isLoading}
										>
											<RefreshCw size={16} />
											Regenerate Explanation
										</Menu.Item>
									</Menu.Content>
								</Menu.Positioner>
							</Portal>
						</Menu.Root>
						<CloseButton onClick={onClose} />
					</Box>
				</Box>
			</Stack>

			{/* Content */}
			<Stack p={4} gap={4} flex={1} overflowY="auto">
				{/* Context Information */}
				<Box>
					<Text fontSize="sm" fontWeight="bold" color="gray.600" mb={2}>
						Context
					</Text>
					<Stack
						gap={0}
						fontSize="sm"
						borderRadius="md"
						overflow="hidden"
						border="1px solid"
						borderColor="gray.200"
					>
						{precedingSegment && (
							<Box
								p={3}
								bg="gray.50"
								borderBottomWidth="1px"
								borderBottomColor="gray.100"
							>
								<Text fontFamily="mono" fontSize="xs" color="gray.500" mb={1}>
									{precedingSegment.src}
								</Text>
								<Text color="gray.500">{precedingSegment.tgt}</Text>
							</Box>
						)}

						<Box
							p={3}
							bg="blue.50"
							borderLeftWidth="4px"
							borderLeftColor="blue.400"
							position="relative"
						>
							<Text
								fontFamily="mono"
								fontSize="xs"
								color="gray.800"
								mb={1}
								fontWeight="medium"
							>
								{currentSegment.src}
							</Text>
							<Text color="gray.800" fontWeight="medium">
								{currentSegment.tgt}
							</Text>
						</Box>

						{followingSegment && (
							<Box
								p={3}
								bg="gray.50"
								borderTopWidth="1px"
								borderTopColor="gray.100"
							>
								<Text fontFamily="mono" fontSize="xs" color="gray.500" mb={1}>
									{followingSegment.src}
								</Text>
								<Text color="gray.500">{followingSegment.tgt}</Text>
							</Box>
						)}
					</Stack>
				</Box>

				<Box>
					{explanation || isLoading || error ? null : (
						<Text fontSize="sm" color="gray.500" fontStyle="italic">
							Select a segment to explain...
						</Text>
					)}

					{isLoading && !explanation && (
						<Center py={8}>
							<Stack alignItems="center" gap={2}>
								<Box
									as={Loader}
									fontSize="2xl"
									color="blue.500"
									animation="spin 1s linear infinite"
								/>
								<Text fontSize="sm" color="gray.600">
									Generating explanation...
								</Text>
							</Stack>
						</Center>
					)}

					{error && (
						<Box
							p={3}
							bg="red.50"
							borderRadius="md"
							borderLeftWidth="3px"
							borderLeftColor="red.400"
						>
							<Text fontSize="sm" color="red.700">
								{error}
							</Text>
						</Box>
					)}

					{explanation && (
						<Box fontSize="sm" lineHeight="1.6" color="gray.700">
							<ReactMarkdown>{explanation}</ReactMarkdown>
							{isLoading && (
								<Text fontSize="xs" color="gray.400" mt={2} fontStyle="italic">
									...
								</Text>
							)}
						</Box>
					)}
				</Box>
			</Stack>
		</Box>
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
						setError("Connection lost while generating explanation");
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
