import {
	Box,
	Button,
	Center,
	DialogBackdrop,
	DialogBody,
	DialogCloseTrigger,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogPositioner,
	DialogRoot,
	DialogTitle,
	HStack,
	Stack,
	Text,
	Textarea,
	VStack,
} from "@chakra-ui/react";
import { Loader, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { client } from "../../../client/client.gen";

interface SegmentContext {
	src: string;
	tgt: string;
}

interface RetranslateModalProps {
	segmentId: number;
	workId: number;
	chapterId: number;
	isOpen: boolean;
	onClose: () => void;
	onRetranslateComplete: () => void;
}

export function RetranslateModal({
	segmentId,
	workId,
	chapterId,
	isOpen,
	onClose,
	onRetranslateComplete,
}: RetranslateModalProps) {
	const [instruction, setInstruction] = useState("");
	const [currentSegment, setCurrentSegment] = useState<SegmentContext | null>(
		null,
	);
	const [contextLoading, setContextLoading] = useState(false);
	const [isRetranslating, setIsRetranslating] = useState(false);
	const [streamedText, setStreamedText] = useState("");
	const [error, setError] = useState<string | null>(null);
	const eventSourceRef = useRef<EventSource | null>(null);

	// Load segment context when modal opens
	useEffect(() => {
		if (!isOpen) {
			setCurrentSegment(null);
			setInstruction("");
			setStreamedText("");
			setError(null);
			setIsRetranslating(false);
			if (eventSourceRef.current) {
				eventSourceRef.current.close();
				eventSourceRef.current = null;
			}
			return;
		}

		let cancelled = false;
		const controller = new AbortController();

		const loadContext = async () => {
			setContextLoading(true);
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
				const segment = payload.segments.find((s) => s.id === segmentId);
				if (segment) {
					setCurrentSegment({ src: segment.src || "", tgt: segment.tgt || "" });
				}
			} catch {
				if (!cancelled) {
					setError("Failed to load segment context");
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

	const handleRetranslate = useCallback(() => {
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
		}

		setIsRetranslating(true);
		setStreamedText("");
		setError(null);

		const params = new URLSearchParams();
		if (instruction.trim()) {
			params.set("instruction", instruction.trim());
		}

		const baseUrl = `/api/works/${workId}/chapters/${chapterId}/segments/${segmentId}/retranslate/stream`;
		const url = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;

		const eventSource = new EventSource(url);
		eventSourceRef.current = eventSource;

		eventSource.addEventListener("segment-delta", (event) => {
			const { delta } = JSON.parse(event.data);
			setStreamedText((prev) => prev + (delta || ""));
		});

		eventSource.addEventListener("segment-complete", () => {
			// Don't close yet, wait for translation-complete
		});

		eventSource.addEventListener("translation-complete", () => {
			eventSource.close();
			eventSourceRef.current = null;
			setIsRetranslating(false);
			onRetranslateComplete();
			onClose();
		});

		eventSource.addEventListener("translation-error", (event) => {
			const { error: errMsg } = JSON.parse(event.data);
			setError(errMsg || "Failed to retranslate segment");
			eventSource.close();
			eventSourceRef.current = null;
			setIsRetranslating(false);
		});

		eventSource.onerror = () => {
			if (eventSourceRef.current) {
				setError("Connection lost during retranslation");
				eventSource.close();
				eventSourceRef.current = null;
				setIsRetranslating(false);
			}
		};
	}, [
		workId,
		chapterId,
		segmentId,
		instruction,
		onRetranslateComplete,
		onClose,
	]);

	const handleCancel = useCallback(() => {
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
			eventSourceRef.current = null;
		}
		setIsRetranslating(false);
		onClose();
	}, [onClose]);

	if (!isOpen) {
		return null;
	}

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(e) => !e.open && handleCancel()}
			size="lg"
		>
			<DialogBackdrop />
			<DialogPositioner>
				<DialogContent>
					<DialogCloseTrigger />
					<DialogHeader borderBottomWidth="1px" pb={4}>
						<Stack direction="row" align="center" gap={2}>
							<RotateCcw size={18} />
							<DialogTitle>Edit Translation</DialogTitle>
						</Stack>
					</DialogHeader>

					<DialogBody py={6}>
						<VStack gap={5} align="stretch">
							{/* Current Segment Display */}
							<Box>
								<Text
									fontSize="xs"
									textTransform="uppercase"
									fontWeight="bold"
									color="gray.500"
									letterSpacing="wider"
									mb={2}
								>
									Current Segment
								</Text>
								{contextLoading ? (
									<Center py={4}>
										<Loader size={20} className="animate-spin" />
									</Center>
								) : currentSegment ? (
									<Box
										p={4}
										bg="gray.50"
										borderRadius="md"
										borderWidth="1px"
										borderColor="gray.200"
									>
										<Text
											fontSize="sm"
											fontFamily="mono"
											color="gray.600"
											mb={2}
										>
											{currentSegment.src}
										</Text>
										<Box
											borderTopWidth="1px"
											borderColor="gray.200"
											pt={2}
											mt={2}
										>
											{isRetranslating ? (
												<Text fontSize="sm" color="gray.800">
													{streamedText || "..."}
													<Text
														as="span"
														color="blue.400"
														animation="pulse 1s infinite"
													>
														▋
													</Text>
												</Text>
											) : (
												<Text fontSize="sm" color="gray.800">
													{currentSegment.tgt || (
														<Text as="span" fontStyle="italic" color="gray.400">
															No translation yet
														</Text>
													)}
												</Text>
											)}
										</Box>
									</Box>
								) : error ? (
									<Text color="red.500" fontSize="sm">
										{error}
									</Text>
								) : null}
							</Box>

							{/* Instruction Input */}
							<Box>
								<Text
									fontSize="xs"
									textTransform="uppercase"
									fontWeight="bold"
									color="gray.500"
									letterSpacing="wider"
									mb={2}
								>
									Instructions (Optional)
								</Text>
								<Textarea
									value={instruction}
									onChange={(e) => setInstruction(e.target.value)}
									placeholder="e.g., Make it more casual, Keep the honorific, Use a different word for..."
									rows={3}
									disabled={isRetranslating}
								/>
								<Text fontSize="xs" color="gray.400" mt={1}>
									Guide how the translation should be adjusted
								</Text>
							</Box>

							{error && !contextLoading && (
								<Box
									p={3}
									bg="red.50"
									color="red.600"
									borderRadius="md"
									fontSize="sm"
								>
									{error}
								</Box>
							)}
						</VStack>
					</DialogBody>

					<DialogFooter borderTopWidth="1px" pt={4}>
						<HStack gap={3}>
							<Button
								variant="ghost"
								onClick={handleCancel}
								disabled={isRetranslating}
							>
								Cancel
							</Button>
							<Button
								colorPalette="teal"
								onClick={handleRetranslate}
								loading={isRetranslating}
								loadingText="Retranslating..."
								disabled={contextLoading || !currentSegment}
							>
								<RotateCcw size={16} />
								Retranslate
							</Button>
						</HStack>
					</DialogFooter>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}
