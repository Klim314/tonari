import {
	Alert,
	Badge,
	Box,
	Button,
	Flex,
	HStack,
	Heading,
	Icon,
	Separator,
	Text,
} from "@chakra-ui/react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import {
	type TranslationStreamStatus,
	useChapterTranslationStream,
} from "../../../hooks/useChapterTranslationStream";
import { ExplanationPanel } from "./ExplanationPanel";
import { SegmentsList } from "./SegmentsList";

type PrimaryAction = "start" | "resume" | "regenerate";

export interface TranslationPanelProps {
	workId: number;
	chapterId: number;
	refreshKey?: number;
}

export const TranslationPanel = memo(function TranslationPanel({
	workId,
	chapterId,
	refreshKey = 0,
}: TranslationPanelProps) {
	const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(
		null,
	);
	const [retranslatingSegmentId, setRetranslatingSegmentId] = useState<
		number | null
	>(null);
	const [explanationSegmentId, setExplanationSegmentId] = useState<
		number | null
	>(null);
	const {
		status: translationStatus,
		error: translationError,
		segments: translationSegments,
		isStreaming,
		start,
		pause,
		isResetting,
		regenerate,
		retranslateSegment,
	} = useChapterTranslationStream({ workId, chapterId });

	useEffect(() => {
		if (!isStreaming) {
			setRetranslatingSegmentId(null);
		}
	}, [isStreaming]);

	useEffect(() => {
		if (!refreshKey) return;
		void regenerate();
	}, [refreshKey, regenerate]);

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
		// If no segments have been translated yet, show "Start"
		if (completedCount === 0) {
			return "start";
		}
		// If some but not all segments are translated, show "Resume"
		return "resume";
	}, [translationSegments, translationStatus]);

	const startTranslation = useCallback(() => {
		start();
	}, [start]);

	const handleRegenerate = useCallback(async () => {
		const ok = await regenerate();
		if (ok) {
			startTranslation();
		}
	}, [regenerate, startTranslation]);

	const handlePrimaryAction = useCallback(async () => {
		if (isStreaming) {
			pause();
			return;
		}
		if (primaryAction === "regenerate") {
			await handleRegenerate();
			return;
		}
		startTranslation();
	}, [handleRegenerate, isStreaming, pause, primaryAction, startTranslation]);

	const primaryLabel = isStreaming
		? "Pause Translation"
		: getPrimaryActionLabel(primaryAction);
	const primaryIcon = isStreaming
		? Pause
		: primaryAction === "regenerate"
			? RotateCcw
			: Play;
	const primaryColorScheme = isStreaming
		? "gray"
		: primaryAction === "regenerate"
			? "orange"
			: "teal";
	const isPrimaryLoading =
		primaryAction === "regenerate" && !isStreaming && isResetting;

	const handleSegmentContextSelect = useCallback((segmentId: number) => {
		setSelectedSegmentId(segmentId);
	}, []);

	const handleClearSelection = useCallback(() => {
		setSelectedSegmentId(null);
	}, []);

	const handleSegmentRetranslate = useCallback(
		(segmentId: number) => {
			setRetranslatingSegmentId(segmentId);
			retranslateSegment(segmentId);
		},
		[retranslateSegment],
	);

	const handleSegmentExplain = useCallback((segmentId: number) => {
		setExplanationSegmentId(segmentId);
	}, []);

	return (
		<Box
			flex="1"
			w="full"
			borderWidth="1px"
			borderRadius="lg"
			px={6}
			pt={4}
			pb={6}
			onClick={handleClearSelection}
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
					Start streaming to generate LangChain-powered translations aligned
					with each newline-delimited source segment.
				</Text>
			) : (
				<SegmentsList
					segments={translationSegments}
					selectedSegmentId={selectedSegmentId}
					retranslatingSegmentId={retranslatingSegmentId}
					onContextSelect={handleSegmentContextSelect}
					onSegmentRetranslate={handleSegmentRetranslate}
					onSegmentExplain={handleSegmentExplain}
				/>
			)}

			{explanationSegmentId !== null && (
				<ExplanationPanel
					segmentId={explanationSegmentId}
					workId={workId}
					chapterId={chapterId}
					currentSegment={{
						src:
							translationSegments.find(
								(s) => s.segmentId === explanationSegmentId,
							)?.src || "",
						tgt:
							translationSegments.find(
								(s) => s.segmentId === explanationSegmentId,
							)?.text || "",
					}}
					precedingSegment={
						translationSegments
							.filter((s) => s.segmentId < explanationSegmentId)
							.slice(-1)
							.map((s) => ({
								src: s.src || "",
								tgt: s.text || "",
							}))[0]
					}
					followingSegment={
						translationSegments
							.filter((s) => s.segmentId > explanationSegmentId)
							.slice(0, 1)
							.map((s) => ({
								src: s.src || "",
								tgt: s.text || "",
							}))[0]
					}
					isOpen={explanationSegmentId !== null}
					onClose={() => setExplanationSegmentId(null)}
				/>
			)}
		</Box>
	);
});

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
