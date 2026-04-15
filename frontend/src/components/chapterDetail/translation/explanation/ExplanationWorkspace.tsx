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
	Flex,
	HStack,
	IconButton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { ChevronLeft, ChevronRight, Loader, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Works } from "../../../../client/sdk.gen";
import type { TranslationSegmentOut } from "../../../../client/types.gen";
import { ExplanationToolbar } from "./ExplanationToolbar";
import { FacetContent } from "./FacetContent";
import { FacetRail } from "./FacetRail";
import { type SentenceRange, SourcePane } from "./SourcePane";
import type { FacetsState, FacetType } from "./types";
import { useExplanationArtifact } from "./useExplanationArtifact";

interface ExplanationWorkspaceProps {
	workId: number;
	chapterId: number;
	segmentId: number;
	isOpen: boolean;
	onClose: () => void;
}

type ChapterSegment = TranslationSegmentOut;

function resolveSentences(segment: ChapterSegment | null): SentenceRange[] {
	if (!segment) return [];
	if (segment.sentences && segment.sentences.length > 0)
		return segment.sentences;
	if (!segment.src) return [];
	return [{ span_start: 0, span_end: segment.src.length, text: segment.src }];
}

export function ExplanationWorkspace({
	workId,
	chapterId,
	segmentId: initialSegmentId,
	isOpen,
	onClose,
}: ExplanationWorkspaceProps) {
	const [segments, setSegments] = useState<ChapterSegment[]>([]);
	const [loadingContext, setLoadingContext] = useState(false);
	const [contextError, setContextError] = useState<string | null>(null);
	const [segmentId, setSegmentId] = useState<number>(initialSegmentId);
	const [sentenceIndex, setSentenceIndex] = useState(0);
	const [activeFacet, setActiveFacet] = useState<FacetType>("overview");

	useEffect(() => {
		if (!isOpen) {
			setSegments([]);
			setContextError(null);
			return;
		}
		const controller = new AbortController();
		let cancelled = false;
		setLoadingContext(true);
		setContextError(null);

		const load = async () => {
			try {
				const resp =
					await Works.getChapterTranslationStateWorksWorkIdChaptersChapterIdTranslationGet(
						{
							path: { work_id: workId, chapter_id: chapterId },
							signal: controller.signal,
							throwOnError: true,
						},
					);
				if (cancelled) return;
				const ordered = [...resp.data.segments].sort(
					(a, b) => a.order_index - b.order_index,
				);
				setSegments(ordered);
			} catch (err) {
				if (cancelled) return;
				if (err instanceof Error && err.name === "AbortError") return;
				setContextError(
					err instanceof Error ? err.message : "failed to load chapter context",
				);
			} finally {
				if (!cancelled) setLoadingContext(false);
			}
		};

		void load();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [isOpen, workId, chapterId]);

	const segmentIndex = segments.findIndex((s) => s.id === segmentId);
	const currentSegment = segmentIndex >= 0 ? segments[segmentIndex] : null;

	const sentences = resolveSentences(currentSegment);

	const safeSentenceIndex = Math.min(
		Math.max(0, sentenceIndex),
		Math.max(0, sentences.length - 1),
	);
	const activeSentence = sentences[safeSentenceIndex];

	const canFetch = Boolean(
		isOpen &&
			currentSegment &&
			sentences.length > 0 &&
			activeSentence &&
			currentSegment.tgt,
	);

	const { status, error, facets, regenerate, isRegenerating } =
		useExplanationArtifact({
			workId,
			chapterId,
			segmentId,
			spanStart: activeSentence?.span_start ?? 0,
			spanEnd: activeSentence?.span_end ?? 1,
			density: "sparse",
			enabled: canFetch,
		});

	const goToSegment = useCallback(
		(nextIndex: number) => {
			const target = segments[nextIndex];
			if (!target) return;
			setSegmentId(target.id);
			setSentenceIndex(0);
		},
		[segments],
	);

	const handlePrevSegment = useCallback(() => {
		if (segmentIndex > 0) goToSegment(segmentIndex - 1);
	}, [segmentIndex, goToSegment]);

	const handleNextSegment = useCallback(() => {
		if (segmentIndex >= 0 && segmentIndex < segments.length - 1) {
			goToSegment(segmentIndex + 1);
		}
	}, [segmentIndex, segments.length, goToSegment]);

	const handleStepBack = useCallback(() => {
		if (safeSentenceIndex > 0) {
			setSentenceIndex((n) => Math.max(0, n - 1));
			return;
		}
		if (segmentIndex <= 0) return;
		const target = segments[segmentIndex - 1];
		if (!target) return;
		const prevSentences = resolveSentences(target);
		setSegmentId(target.id);
		setSentenceIndex(Math.max(0, prevSentences.length - 1));
	}, [safeSentenceIndex, segmentIndex, segments]);

	const handleStepForward = useCallback(() => {
		if (safeSentenceIndex < sentences.length - 1) {
			setSentenceIndex((n) => Math.min(sentences.length - 1, n + 1));
			return;
		}
		if (segmentIndex >= 0 && segmentIndex < segments.length - 1) {
			goToSegment(segmentIndex + 1);
		}
	}, [
		safeSentenceIndex,
		sentences.length,
		segmentIndex,
		segments.length,
		goToSegment,
	]);

	useEffect(() => {
		if (!isOpen) return;
		const onKey = (e: KeyboardEvent) => {
			const target = e.target as HTMLElement | null;
			if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
			if (target?.isContentEditable) return;
			if (e.key === "ArrowLeft") {
				e.preventDefault();
				handleStepBack();
			} else if (e.key === "ArrowRight") {
				e.preventDefault();
				handleStepForward();
			}
		};
		window.addEventListener("keydown", onKey);
		return () => window.removeEventListener("keydown", onKey);
	}, [isOpen, handleStepBack, handleStepForward]);

	const statusLabel =
		status === "generating"
			? "generating..."
			: status === "loading"
				? "loading..."
				: status === "complete"
					? "cached · sparse"
					: status === "error"
						? "error"
						: undefined;

	const canPrevSegment = segmentIndex > 0;
	const canNextSegment =
		segmentIndex >= 0 && segmentIndex < segments.length - 1;
	const canPrevSentence = safeSentenceIndex > 0;
	const canNextSentence = safeSentenceIndex < sentences.length - 1;

	const regenerateDisabled =
		!canFetch || status === "loading" || status === "generating";

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(e) => !e.open && onClose()}
			size="full"
			scrollBehavior="inside"
		>
			<DialogBackdrop />
			<DialogPositioner>
				<DialogContent
					maxW={{ base: "100%", md: "1200px" }}
					maxH={{ base: "100vh", md: "90vh" }}
					m={{ base: 0, md: 6 }}
				>
					<DialogCloseTrigger />
					<DialogHeader borderBottomWidth="1px" pb={3}>
						<HStack gap={2} align="center">
							<DialogTitle>Explanation Workspace</DialogTitle>
							<Badge colorPalette="purple" variant="subtle" size="sm">
								<HStack gap={1}>
									<Sparkles size={10} />
									<Text>AI Tutor</Text>
								</HStack>
							</Badge>
						</HStack>
					</DialogHeader>
					<DialogBody p={0} overflow="hidden">
						{loadingContext && !currentSegment ? (
							<LoadingState />
						) : contextError ? (
							<ErrorState message={contextError} />
						) : !currentSegment ? (
							<NotFoundState />
						) : (
							<Flex direction="column" h="full" minH="0">
								<Box
									px={{ base: 4, md: 6 }}
									py={3}
									borderBottomWidth="1px"
									bg="bg.subtle"
								>
									<ExplanationToolbar
										segmentPosition={{
											index: segmentIndex,
											total: segments.length,
										}}
										sentencePosition={
											sentences.length
												? {
														index: safeSentenceIndex,
														total: sentences.length,
													}
												: null
										}
										onPrevSentence={() =>
											setSentenceIndex((n) => Math.max(0, n - 1))
										}
										onNextSentence={() =>
											setSentenceIndex((n) =>
												Math.min(sentences.length - 1, n + 1),
											)
										}
										canPrevSentence={canPrevSentence}
										canNextSentence={canNextSentence}
										onRegenerate={regenerate}
										isRegenerating={isRegenerating}
										regenerateDisabled={regenerateDisabled}
									/>
								</Box>

								<Flex
									direction={{ base: "column", md: "row" }}
									flex="1"
									minH="0"
									position="relative"
								>
									<EdgeNav
										direction="prev"
										onClick={handlePrevSegment}
										disabled={!canPrevSegment}
									/>
									<EdgeNav
										direction="next"
										onClick={handleNextSegment}
										disabled={!canNextSegment}
									/>

									<SegmentBox
										segment={currentSegment}
										sentences={sentences}
										activeSentenceIndex={safeSentenceIndex}
										activeFacet={activeFacet}
										onFacetChange={setActiveFacet}
										facets={facets}
										canFetch={canFetch}
										error={error}
									/>

									<FacetSidebar
										activeFacet={activeFacet}
										onFacetChange={setActiveFacet}
										facets={facets}
										statusLabel={statusLabel}
									/>
								</Flex>
							</Flex>
						)}
					</DialogBody>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}

function LoadingState() {
	return (
		<Center py={16}>
			<HStack gap={2} color="fg.muted">
				<Box as={Loader} boxSize="16px" animation="spin 1s linear infinite" />
				<Text>Loading chapter...</Text>
			</HStack>
		</Center>
	);
}

function ErrorState({ message }: { message: string }) {
	return (
		<Center py={16}>
			<Text color="red.fg" fontSize="sm">
				{message}
			</Text>
		</Center>
	);
}

function NotFoundState() {
	return (
		<Center py={16}>
			<Text color="fg.muted" fontSize="sm">
				Segment not found.
			</Text>
		</Center>
	);
}

interface SegmentBoxProps {
	segment: ChapterSegment;
	sentences: SentenceRange[];
	activeSentenceIndex: number;
	activeFacet: FacetType;
	onFacetChange: (f: FacetType) => void;
	facets: FacetsState;
	canFetch: boolean;
	error: string | null;
}

function SegmentBox({
	segment,
	sentences,
	activeSentenceIndex,
	activeFacet,
	onFacetChange,
	facets,
	canFetch,
	error,
}: SegmentBoxProps) {
	return (
		<Box
			flex="1"
			minW="0"
			overflowY="auto"
			px={{ base: 4, md: 8 }}
			py={{ base: 4, md: 6 }}
		>
			<Stack gap={6}>
				<SourcePane
					source={segment.src}
					translation={segment.tgt}
					sentences={sentences}
					activeSentenceIndex={activeSentenceIndex}
				/>

				<Box
					display={{ base: "block", md: "none" }}
					borderTopWidth="1px"
					pt={4}
				>
					<FacetRail
						active={activeFacet}
						onChange={onFacetChange}
						facets={facets}
						orientation="horizontal"
					/>
				</Box>

				<Box borderTopWidth="1px" pt={4}>
					<SegmentFacetBody
						segment={segment}
						activeFacet={activeFacet}
						facets={facets}
						canFetch={canFetch}
						error={error}
					/>
				</Box>
			</Stack>
		</Box>
	);
}

function SegmentFacetBody({
	segment,
	activeFacet,
	facets,
	canFetch,
	error,
}: {
	segment: ChapterSegment;
	activeFacet: FacetType;
	facets: FacetsState;
	canFetch: boolean;
	error: string | null;
}) {
	if (!canFetch) {
		return (
			<Box
				p={4}
				bg="bg.subtle"
				borderRadius="md"
				fontSize="sm"
				color="fg.muted"
			>
				{segment.tgt
					? "No sentence selected."
					: "This segment has no translation yet. Translate it first."}
			</Box>
		);
	}
	if (error) {
		return (
			<Box p={4} bg="red.subtle" color="red.fg" borderRadius="md" fontSize="sm">
				{error}
			</Box>
		);
	}
	return (
		<FacetContent
			facetType={activeFacet}
			state={
				facets[activeFacet] ?? { status: "pending", data: null, error: null }
			}
		/>
	);
}

interface FacetSidebarProps {
	activeFacet: FacetType;
	onFacetChange: (f: FacetType) => void;
	facets: FacetsState;
	statusLabel: string | undefined;
}

function FacetSidebar({
	activeFacet,
	onFacetChange,
	facets,
	statusLabel,
}: FacetSidebarProps) {
	return (
		<Box
			display={{ base: "none", md: "block" }}
			w="220px"
			flexShrink={0}
			borderLeftWidth="1px"
			bg="bg.subtle"
			py={6}
			px={3}
			overflowY="auto"
		>
			<FacetRail
				active={activeFacet}
				onChange={onFacetChange}
				facets={facets}
				orientation="vertical"
				statusLabel={statusLabel}
			/>
		</Box>
	);
}

function EdgeNav({
	direction,
	onClick,
	disabled,
}: {
	direction: "prev" | "next";
	onClick: () => void;
	disabled: boolean;
}) {
	if (disabled) return null;
	const isPrev = direction === "prev";
	return (
		<IconButton
			aria-label={isPrev ? "Previous segment" : "Next segment"}
			size="sm"
			variant="ghost"
			onClick={onClick}
			position="absolute"
			top="50%"
			transform="translateY(-50%)"
			left={isPrev ? 1 : undefined}
			right={isPrev ? undefined : 1}
			zIndex={1}
			display={{ base: "none", md: "inline-flex" }}
		>
			{isPrev ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
		</IconButton>
	);
}
