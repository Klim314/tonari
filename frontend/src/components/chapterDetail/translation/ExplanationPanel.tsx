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
	const [isLoading, setIsLoading] = useState(false);
	const [explanation, setExplanation] = useState<string>("");
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!isOpen) {
			setExplanation("");
			setError(null);
			return;
		}

		const fetchExplanation = async () => {
			setIsLoading(true);
			setError(null);
			setExplanation("");

			try {
				const url = `/api/works/${workId}/chapters/${chapterId}/segments/${segmentId}/explain/stream`;
				const eventSource = new EventSource(url);

				eventSource.addEventListener("explanation-delta", (event) => {
					const { delta } = JSON.parse(event.data);
					setExplanation((prev) => prev + (delta || ""));
				});

				eventSource.addEventListener("explanation-complete", () => {
					eventSource.close();
					setIsLoading(false);
				});

				eventSource.addEventListener("explanation-error", (event) => {
					const { error } = JSON.parse(event.data);
					setError(error || "Failed to generate explanation");
					eventSource.close();
					setIsLoading(false);
				});

				eventSource.onerror = () => {
					setError("Connection lost while generating explanation");
					eventSource.close();
					setIsLoading(false);
				};

				return () => {
					eventSource.close();
				};
			} catch (err) {
				setError(err instanceof Error ? err.message : "Unknown error occurred");
				setIsLoading(false);
			}
		};

		fetchExplanation();
	}, [isOpen, segmentId, workId, chapterId]);

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

				{/* Explanation */}
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

					{explanation && (
						<Box fontSize="sm" lineHeight="1.6" color="gray.700">
							<ReactMarkdown
								components={{
									p: ({ children }) => (
										<Text mb={2} fontSize="sm">
											{children}
										</Text>
									),
									h1: ({ children }) => (
										<Heading size="sm" mb={2} mt={3}>
											{children}
										</Heading>
									),
									h2: ({ children }) => (
										<Heading size="xs" mb={2} mt={2}>
											{children}
										</Heading>
									),
									h3: ({ children }) => (
										<Text fontWeight="bold" mb={2} fontSize="sm">
											{children}
										</Text>
									),
									ul: ({ children }) => (
										<Box as="ul" mb={2} ps={4} sx={{ listStyleType: "disc" }}>
											{children}
										</Box>
									),
									ol: ({ children }) => (
										<Box as="ol" mb={2} ps={4}>
											{children}
										</Box>
									),
									li: ({ children }) => (
										<Box as="li" fontSize="sm" mb={1}>
											{children}
										</Box>
									),
									strong: ({ children }) => (
										<Box as="strong" fontWeight="bold">
											{children}
										</Box>
									),
									em: ({ children }) => (
										<Box as="em" fontStyle="italic">
											{children}
										</Box>
									),
									code: ({ children }) => (
										<Box
											as="code"
											bg="gray.100"
											px={1}
											py={0.5}
											borderRadius="sm"
											fontFamily="mono"
											fontSize="xs"
											whiteSpace="pre-wrap"
										>
											{children}
										</Box>
									),
									a: ({ href, children }) => (
										<Text
											as="a"
											href={href}
											color="blue.500"
											textDecoration="underline"
											target="_blank"
											rel="noopener noreferrer"
										>
											{children}
										</Text>
									),
								}}
							>
								{explanation}
							</ReactMarkdown>
						</Box>
					)}
				</Box>
			</Stack>
		</Box>
	);
}
