import {
	Alert,
	Badge,
	Box,
	Button,
	Container,
	Flex,
	HStack,
	Heading,
	Icon,
	Separator,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Pause, Play } from "lucide-react";
import { useChapter } from "../hooks/useChapter";
import {
	type TranslationStreamStatus,
	useChapterTranslationStream,
} from "../hooks/useChapterTranslationStream";
import { useWork } from "../hooks/useWork";
import type { Chapter } from "../types/works";

interface ChapterDetailPageProps {
	workId: number;
	chapterId: number;
	onNavigateBack: (path?: string) => void;
}

export function ChapterDetailPage({
	workId,
	chapterId,
	onNavigateBack,
}: ChapterDetailPageProps) {
	const {
		data: work,
		loading: workLoading,
		error: workError,
	} = useWork(workId);
	const {
		data: chapter,
		loading: chapterLoading,
		error: chapterError,
	} = useChapter(workId, chapterId);
	const translation = useChapterTranslationStream({ workId, chapterId });

	const loading = workLoading || chapterLoading;
	const error = workError || chapterError;

	return (
		<Box py={10}>
			<Container maxW="6xl">
				<Button
					variant="ghost"
					mb={4}
					onClick={() => onNavigateBack(`/works/${workId}`)}
				>
					← Back to work
				</Button>

				{loading ? (
					<Stack gap={4}>
						<Skeleton height="32px" borderRadius="md" />
						<Skeleton height="420px" borderRadius="lg" />
					</Stack>
				) : error ? (
					<Alert.Root status="error" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>
								Failed to load chapter: {error}
							</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				) : !work || !chapter ? (
					<Alert.Root status="warning" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>Chapter not found.</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				) : (
					<Stack gap={8}>
						<Box borderWidth="1px" borderRadius="lg" p={6}>
							<Text color="gray.400" fontSize="sm" mb={2}>
								{work.title}
							</Text>
							<Heading size="lg" mb={2}>
								Chapter {formatChapterKey(chapter.idx)}: {chapter.title}
							</Heading>
							<Text color="gray.400" fontSize="sm">
								Sort key {chapter.sort_key.toFixed(4)}
							</Text>
						</Box>

						<Stack
							direction={{ base: "column", lg: "row" }}
							gap={8}
							align="flex-start"
						>
							<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
								<Heading size="md" mb={4}>
									Source Text
								</Heading>
								<Separator mb={4} />
								<Text
									whiteSpace="pre-wrap"
									fontFamily="mono"
									lineHeight="tall"
									color="gray.400"
								>
									{chapter.normalized_text}
								</Text>
							</Box>

							<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
								<Flex
									direction={{ base: "column", md: "row" }}
									align={{ base: "flex-start", md: "center" }}
									justify="space-between"
									gap={4}
									mb={4}
								>
									<HStack gap={2}>
										<Heading size="md">Translation</Heading>
										<Badge
											variant="solid"
											colorPalette={getStatusColorScheme(translation.status)}
										>
											{formatStatusLabel(translation.status)}
										</Badge>
									</HStack>

									<Button
										variant="outline"
										colorScheme={translation.isStreaming ? "gray" : "teal"}
										onClick={
											translation.isStreaming
												? translation.pause
												: translation.start
										}
										disabled={!translation.isStreaming && (!work || !chapter)}
									>
										<HStack gap={2} align="center">
											<Text>{getControlLabel(translation.status)}</Text>
										</HStack>
										<Icon
											as={translation.isStreaming ? Pause : Play}
											boxSize={4}
										/>
									</Button>
								</Flex>
								{translation.error ? (
									<Alert.Root status="error" borderRadius="md" mb={4}>
										<Alert.Indicator />
										<Alert.Content>
											<Alert.Description>{translation.error}</Alert.Description>
										</Alert.Content>
									</Alert.Root>
								) : null}
								<Separator mb={4} />
								{translation.segments.length === 0 ? (
									<Text color="gray.400">
										Start streaming to generate lorem ipsum placeholder
										translations aligned with each newline-delimited source
										segment.
									</Text>
								) : (
									<Stack gap={5}>
										{translation.segments.map((segment) => {
											const srcText = segment.src || "";
											const tgtText =
												segment.text ||
												(segment.status === "running" ? "Translating..." : "");
											const hasSource = srcText.trim().length > 0;
											const hasTarget = tgtText.trim().length > 0;
											if (!hasSource && !hasTarget) {
												return <Box key={segment.segmentId} height="2" />;
											}
											return (
												<Stack key={segment.segmentId} gap={2}>
													{hasSource ? (
														<Text
															fontFamily="mono"
															whiteSpace="pre-wrap"
															color="gray.400"
														>
															{srcText}
														</Text>
													) : null}
													{hasTarget ? (
														<Text whiteSpace="pre-wrap" color="gray.400">
															{tgtText}
														</Text>
													) : null}
												</Stack>
											);
										})}
									</Stack>
								)}
							</Box>
						</Stack>
					</Stack>
				)}
			</Container>
		</Box>
	);
}

function formatChapterKey(key: Chapter["idx"]) {
	if (typeof key === "number") {
		return Number.isInteger(key) ? String(key) : key.toFixed(2);
	}
	return key;
}

function formatStatusLabel(status: TranslationStreamStatus) {
	switch (status) {
		case "connecting":
			return "Connecting";
		case "running":
			return "Streaming";
		case "completed":
			return "Completed";
		case "error":
			return "Error";
		default:
			return "Idle";
	}
}

function getStatusColorScheme(status: TranslationStreamStatus) {
	switch (status) {
		case "connecting":
			return "yellow";
		case "running":
			return "teal";
		case "completed":
			return "green";
		case "error":
			return "red";
		default:
			return "gray";
	}
}

function getControlLabel(status: TranslationStreamStatus) {
	switch (status) {
		case "running":
			return "Pause Translation";
		case "connecting":
			return "Connecting";
		case "completed":
			return "Resume Translation";
		default:
			return "Start Translation";
	}
}
