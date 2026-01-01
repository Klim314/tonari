import {
	Box,
	Center,
	CloseButton,
	Heading,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Loader } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useEffect, useState } from "react";

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
	const { explanation, isLoading, error } = useExplanationStream(
		workId,
		chapterId,
		segmentId,
		isOpen,
	);

	if (!isOpen) {
		return null;
	}

	return (
		<Box
			position="fixed"
			right={0}
			top={0}
			bottom={0}
			width="400px"
			bg="white"
			borderLeftWidth="1px"
			borderLeftColor="gray.200"
			boxShadow="lg"
			overflowY="auto"
			zIndex={1000}
			display="flex"
			flexDirection="column"
		>
			{/* Header */}
			<Stack
				p={4}
				borderBottomWidth="1px"
				borderBottomColor="gray.200"
				gap={2}
				flexShrink={0}
			>
				<Box display="flex" justifyContent="space-between" alignItems="center">
					<Heading size="md">Translation Explanation</Heading>
					<CloseButton onClick={onClose} />
				</Box>
			</Stack>

			{/* Content */}
			<Stack p={4} gap={4} flex={1} overflowY="auto">
				{/* Context Information */}
				<Box>
					<Text fontSize="sm" fontWeight="bold" color="gray.600" mb={2}>
						Context
					</Text>
					<Stack gap={3} fontSize="sm">
						{precedingSegment && (
							<Box
								p={2}
								bg="gray.50"
								borderRadius="md"
								borderLeftWidth="3px"
								borderLeftColor="gray.400"
							>
								<Text color="gray.600" mb={1}>
									<strong>Previous:</strong>
								</Text>
								<Text fontFamily="mono" fontSize="xs" color="gray.700" mb={1}>
									{precedingSegment.src}
								</Text>
								<Text color="gray.600">→ {precedingSegment.tgt}</Text>
							</Box>
						)}

						<Box
							p={2}
							bg="blue.50"
							borderRadius="md"
							borderLeftWidth="3px"
							borderLeftColor="blue.400"
						>
							<Text color="gray.600" mb={1}>
								<strong>Current (Being Explained):</strong>
							</Text>
							<Text fontFamily="mono" fontSize="xs" color="gray.700" mb={1}>
								{currentSegment.src}
							</Text>
							<Text color="gray.600">→ {currentSegment.tgt}</Text>
						</Box>

						{followingSegment && (
							<Box
								p={2}
								bg="gray.50"
								borderRadius="md"
								borderLeftWidth="3px"
								borderLeftColor="gray.400"
							>
								<Text color="gray.600" mb={1}>
									<strong>Next:</strong>
								</Text>
								<Text fontFamily="mono" fontSize="xs" color="gray.700" mb={1}>
									{followingSegment.src}
								</Text>
								<Text color="gray.600">→ {followingSegment.tgt}</Text>
							</Box>
						)}
					</Stack>
				</Box>

				<Box>
					<Text fontSize="sm" fontWeight="bold" color="gray.600" mb={2}>
						Explanation
					</Text>

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

					{
						explanation && (
							<Box fontSize="sm" lineHeight="1.6" color="gray.700">
								<ReactMarkdown>{explanation}</ReactMarkdown>
								{isLoading && (
									<Text fontSize="xs" color="gray.400" mt={2} fontStyle="italic">
										...
									</Text>
								)}
							</Box>
						)
					}
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

	useEffect(() => {
		if (!isOpen) {
			setExplanation("");
			setError(null);
			return;
		}

		setIsLoading(true);
		setError(null);
		setExplanation("");

		let eventSource: EventSource | null = null;

		try {
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
		} catch (err) {
			setError(err instanceof Error ? err.message : "Unknown error occurred");
			setIsLoading(false);
		}

		return () => {
			if (eventSource) {
				eventSource.close();
			}
		};
	}, [isOpen, segmentId, workId, chapterId]);

	return { explanation, isLoading, error };
}
