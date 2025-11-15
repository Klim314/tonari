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
	Menu,
	Portal,
	Separator,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Pause, Play, RotateCcw, Settings } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useChapter } from "../hooks/useChapter";
import {
	type TranslationStreamStatus,
	useChapterTranslationStream,
} from "../hooks/useChapterTranslationStream";
import { useWork } from "../hooks/useWork";
import type { Chapter } from "../types/works";

type PrimaryAction = "start" | "resume" | "regenerate";

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
	const [isRegeneratingSegments, setIsRegeneratingSegments] = useState(false);
	const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(null);
	const [retranslatingSegmentId, setRetranslatingSegmentId] = useState<number | null>(null);
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
	const {
		status: translationStatus,
		error: translationError,
		segments: translationSegments,
		isStreaming: isTranslationStreaming,
		start: startTranslation,
		pause: pauseTranslation,
		isResetting: translationResetting,
		regenerate: regenerateTranslation,
		retranslateSegment,
	} = useChapterTranslationStream({ workId, chapterId });

	const handleRegenerate = useCallback(async () => {
		const ok = await regenerateTranslation();
		if (ok) {
			startTranslation();
		}
	}, [regenerateTranslation, startTranslation]);

	const handleRegenerateSegments = useCallback(async () => {
		if (!workId || !chapterId) return;
		setIsRegeneratingSegments(true);
		try {
			const response = await fetch(
				`/api/works/${workId}/chapters/${chapterId}/regenerate-segments`,
				{ method: "POST" },
			);
			if (!response.ok) {
				throw new Error("Failed to regenerate segments");
			}
			// Refresh translations after regenerating segments
			await regenerateTranslation();
		} catch (error) {
			console.error("Error regenerating segments:", error);
		} finally {
			setIsRegeneratingSegments(false);
		}
	}, [workId, chapterId, regenerateTranslation]);

	// Clear retranslating state when translation completes or errors
	useEffect(() => {
		if (!isTranslationStreaming) {
			setRetranslatingSegmentId(null);
		}
	}, [isTranslationStreaming]);

	const primaryAction = useMemo<PrimaryAction>(() => {
		const translatableSegments = translationSegments.filter(
			(segment) => (segment.src ?? "").trim().length > 0,
		);
		if (translationStatus === "completed") {
			return "regenerate";
		}
		if (translatableSegments.length === 0) {
			return "start";
		}
		const completedCount = translatableSegments.filter(
			(segment) =>
				segment.status === "completed" &&
				(segment.text ?? "").trim().length > 0,
		).length;
		if (completedCount === translatableSegments.length) {
			return "regenerate";
		}
		return "resume";
	}, [translationSegments, translationStatus]);

	const handlePrimaryAction = useCallback(async () => {
		if (isTranslationStreaming) {
			pauseTranslation();
			return;
		}
		if (primaryAction === "regenerate") {
			await handleRegenerate();
			return;
		}
		startTranslation();
	}, [
		handleRegenerate,
		isTranslationStreaming,
		pauseTranslation,
		primaryAction,
		startTranslation,
	]);

	const primaryLabel = isTranslationStreaming
		? "Pause Translation"
		: getPrimaryActionLabel(primaryAction);
	const primaryIcon = isTranslationStreaming
		? Pause
		: primaryAction === "regenerate"
			? RotateCcw
			: Play;
	const primaryColorScheme = isTranslationStreaming
		? "gray"
		: primaryAction === "regenerate"
			? "orange"
			: "teal";
	const isPrimaryLoading =
		primaryAction === "regenerate" &&
		!isTranslationStreaming &&
		translationResetting;

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
						<Box borderWidth="1px" borderRadius="lg" p={6} position="relative">
							<Text color="gray.400" fontSize="sm" mb={2}>
								{work.title}
							</Text>
							<Heading size="lg" mb={2}>
								Chapter {formatChapterKey(chapter.idx)}: {chapter.title}
							</Heading>
							<Text color="gray.400" fontSize="sm" mb={4}>
								Sort key {chapter.sort_key.toFixed(4)}
							</Text>
							<Box position="absolute" top={4} right={4}>
								<Menu.Root positioning={{ placement: "bottom-end" }}>
									<Menu.Trigger asChild>
										<Button
											variant="outline"
											size="sm"
											disabled={!work || !chapter}
										>
											<Icon as={Settings} boxSize={4} />
										</Button>
									</Menu.Trigger>
									<Menu.Positioner>
										<Menu.Content>
											<Menu.Item
												value="regenerate-segments"
												onClick={handleRegenerateSegments}
												disabled={isRegeneratingSegments}
											>
												Regenerate Segments
											</Menu.Item>
										</Menu.Content>
									</Menu.Positioner>
								</Menu.Root>
							</Box>
						</Box>

						<Stack
							direction={{ base: "column", lg: "row" }}
							gap={8}
							align="flex-start"
						>
							<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
								<Heading size="md" mb={4} h="8">
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

							<Box
								flex="1"
								w="full"
								borderWidth="1px"
								borderRadius="lg"
								px={6}
								pt={4}
								pb={6}
								onClick={() => setSelectedSegmentId(null)}
							>
								<Flex
									direction={{ base: "column", md: "row" }}
									align={{ base: "flex-start", md: "center" }}
									justify="space-between"
									gap={4}
									mb={4}
									minH="10"
								>
									<HStack gap={2}>
										<Heading size="md">Translation</Heading>
										<Badge
											variant="solid"
											colorPalette={getStatusColorScheme(translationStatus)}
										>
											{formatStatusLabel(translationStatus)}
										</Badge>
									</HStack>

									<HStack gap={3} flexWrap="wrap">
										<Button
											variant="outline"
											colorScheme={primaryColorScheme}
											onClick={handlePrimaryAction}
											loading={isPrimaryLoading}
											disabled={!isTranslationStreaming && (!work || !chapter)}
										>
											<HStack gap={2} align="center">
												<Text>{primaryLabel}</Text>
											</HStack>
											<Icon as={primaryIcon} boxSize={4} />
										</Button>
									</HStack>
								</Flex>
								{translationError ? (
									<Alert.Root status="error" borderRadius="md" mb={4}>
										<Alert.Indicator />
										<Alert.Content>
											<Alert.Description>{translationError}</Alert.Description>
										</Alert.Content>
									</Alert.Root>
								) : null}
								<Separator mb={4} />
								{translationSegments.length === 0 ? (
									<Text color="gray.400">
										Start streaming to generate LangChain-powered translations
										aligned with each newline-delimited source segment.
									</Text>
								) : (
									<Stack gap={5}>
										{translationSegments.map((segment) => {
											const srcText = segment.src || "";
											const tgtText =
												segment.text ||
												(segment.status === "running" ? "Translating..." : "");
											const hasSource = srcText.trim().length > 0;
											const hasTarget = tgtText.trim().length > 0;
											const isSelected = selectedSegmentId === segment.segmentId;
											const isRetranslating =
												retranslatingSegmentId === segment.segmentId;
											if (!hasSource && !hasTarget) {
												return <Box key={segment.segmentId} height="2" />;
											}
											return (
												<Menu.Root key={segment.segmentId}>
													<Menu.ContextTrigger
														w="full"
														bg={isSelected ? "blue.50" : "transparent"}
														borderRadius="md"
														p={3}
														borderWidth={isSelected ? "1px" : "0px"}
														borderColor={isSelected ? "blue.200" : "transparent"}
														cursor="context-menu"
														onContextMenu={() => setSelectedSegmentId(segment.segmentId)}
													>
														<Stack gap={2}>
															{hasSource ? (
																<Text
																	fontFamily="mono"
																	whiteSpace="pre-wrap"
																	color="gray.400"
																	textAlign="left"
																>
																	{srcText}
																</Text>
															) : null}
															{hasTarget ? (
																<Text
																	whiteSpace="pre-wrap"
																	color="gray.400"
																	textAlign="left"
																>
																	{tgtText}
																</Text>
															) : null}
														</Stack>
													</Menu.ContextTrigger>
													<Portal>
														<Menu.Positioner>
															<Menu.Content>
																<Menu.Item
																	value="retranslate"
																	onClick={() => {
																		setRetranslatingSegmentId(
																			segment.segmentId
																		);
																		retranslateSegment(segment.segmentId);
																	}}
																	disabled={isRetranslating}
																>
																	{isRetranslating
																		? "Retranslating..."
																		: "Retranslate Segment"}
																</Menu.Item>
															</Menu.Content>
														</Menu.Positioner>
													</Portal>
												</Menu.Root>
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

function getPrimaryActionLabel(action: PrimaryAction) {
	switch (action) {
		case "resume":
			return "Resume Translation";
		case "regenerate":
			return "Regenerate Translation";
		default:
			return "Start Translation";
	}
}
