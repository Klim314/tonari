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
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Prompts } from "../client";
import { ChapterPromptDrawer } from "../components/ChapterPromptDrawer";
import { useChapter } from "../hooks/useChapter";
import {
	type TranslationStreamStatus,
	useChapterTranslationStream,
} from "../hooks/useChapterTranslationStream";
import { useWork } from "../hooks/useWork";
import { useWorkPromptDetail } from "../hooks/useWorkPromptDetail";
import { getApiErrorMessage } from "../lib/api";
import type { Chapter } from "../types/works";

type PrimaryAction = "start" | "resume" | "regenerate";

interface ChapterDetailPageProps {
	workId: number;
	chapterId: number;
	onNavigateBack: (path?: string) => void;
}

type TranslationSegmentRow = ReturnType<
	typeof useChapterTranslationStream
>["segments"][number];

interface ChapterPromptOverrideResponse {
	token: string;
	expires_at: string;
}

export function ChapterDetailPage({
	workId,
	chapterId,
	onNavigateBack,
}: ChapterDetailPageProps) {
	const [isRegeneratingSegments, setIsRegeneratingSegments] = useState(false);
	const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(
		null,
	);
	const [retranslatingSegmentId, setRetranslatingSegmentId] = useState<
		number | null
	>(null);
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
	const {
		data: workPrompt,
		loading: workPromptLoading,
		error: workPromptError,
		notAssigned: workPromptNotAssigned,
		refresh: refreshWorkPrompt,
	} = useWorkPromptDetail(workId);
	const [promptDraft, setPromptDraft] = useState({ model: "", template: "" });
	const [promptBaseline, setPromptBaseline] = useState({
		model: "",
		template: "",
	});
	const [promptSaving, setPromptSaving] = useState(false);
	const [promptSaveError, setPromptSaveError] = useState<string | null>(null);
	const [promptRunError, setPromptRunError] = useState<string | null>(null);
	const promptPristineRef = useRef(true);

	useEffect(() => {
		const latestModel = workPrompt?.latest_version?.model ?? "";
		const latestTemplate = workPrompt?.latest_version?.template ?? "";
		const nextBaseline = { model: latestModel, template: latestTemplate };
		setPromptBaseline(nextBaseline);
		if (promptPristineRef.current) {
			setPromptDraft(nextBaseline);
			setPromptSaveError(null);
			setPromptRunError(null);
		}
	}, [workPrompt]);
	const isPromptDirty =
		promptDraft.model !== promptBaseline.model ||
		promptDraft.template !== promptBaseline.template;
	useEffect(() => {
		promptPristineRef.current = !isPromptDirty;
	}, [isPromptDirty]);
	const canOverridePrompt =
		promptDraft.model.trim().length > 0 &&
		promptDraft.template.trim().length > 0;
	const promptDraftRef = useRef(promptDraft);
	const isPromptDirtyRef = useRef(isPromptDirty);
	const canOverridePromptRef = useRef(canOverridePrompt);
	useEffect(() => {
		promptDraftRef.current = promptDraft;
	}, [promptDraft]);
	useEffect(() => {
		isPromptDirtyRef.current = isPromptDirty;
	}, [isPromptDirty]);
	useEffect(() => {
		canOverridePromptRef.current = canOverridePrompt;
	}, [canOverridePrompt]);

	const preparePromptOverrideToken = useCallback(async (): Promise<{
		token: string | null;
		shouldAbort: boolean;
	}> => {
		if (!isPromptDirtyRef.current) {
			return { token: null, shouldAbort: false };
		}
		if (!canOverridePromptRef.current) {
			setPromptRunError("Model and template are required to run this prompt.");
			return { token: null, shouldAbort: true };
		}
		setPromptRunError(null);
		const url = `/api/works/${workId}/chapters/${chapterId}/prompt-overrides`;
		try {
			const response = await fetch(url, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					model: promptDraftRef.current.model,
					template: promptDraftRef.current.template,
				}),
			});
			if (!response.ok) {
				const detail = await parseErrorResponse(response);
				setPromptRunError(detail || "Failed to prepare prompt override.");
				return { token: null, shouldAbort: true };
			}
			const data = (await response.json()) as ChapterPromptOverrideResponse;
			return { token: data.token ?? null, shouldAbort: false };
		} catch (error) {
			setPromptRunError(
				getApiErrorMessage(error, "Failed to prepare prompt override."),
			);
			return { token: null, shouldAbort: true };
		}
	}, [chapterId, workId]);

	const startTranslationWithPrompt = useCallback(async () => {
		const { token, shouldAbort } = await preparePromptOverrideToken();
		if (shouldAbort) {
			return;
		}
		startTranslation({
			promptOverrideToken: token ?? undefined,
		});
	}, [preparePromptOverrideToken, startTranslation]);

	const handleRegenerate = useCallback(async () => {
		const ok = await regenerateTranslation();
		if (ok) {
			await startTranslationWithPrompt();
		}
	}, [regenerateTranslation, startTranslationWithPrompt]);

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
		await startTranslationWithPrompt();
	}, [
		handleRegenerate,
		isTranslationStreaming,
		pauseTranslation,
		primaryAction,
		startTranslationWithPrompt,
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

	const promptName = workPrompt?.name ?? undefined;
	const promptLastSavedAt = workPrompt?.latest_version?.created_at
		? new Date(workPrompt.latest_version.created_at)
		: null;
	const saveDisabledReason = !workPrompt
		? "Assign a prompt to this work before saving changes."
		: !canOverridePrompt && isPromptDirty
			? "Model and template are required."
			: null;
	const disablePrimaryAction = !isTranslationStreaming && (!work || !chapter);

	const loading = workLoading || chapterLoading;
	const error = workError || chapterError;

	const handleSegmentContextSelect = useCallback((segmentId: number) => {
		setSelectedSegmentId(segmentId);
	}, []);
	const handleClearSelection = useCallback(() => {
		setSelectedSegmentId(null);
	}, []);

	const handleSegmentRetranslate = useCallback(
		async (segmentId: number) => {
			setRetranslatingSegmentId(segmentId);
			const { token, shouldAbort } = await preparePromptOverrideToken();
			if (shouldAbort) {
				setRetranslatingSegmentId(null);
				return;
			}
			retranslateSegment(segmentId, {
				promptOverrideToken: token ?? undefined,
			});
		},
		[preparePromptOverrideToken, retranslateSegment],
	);
	const handlePromptDraftChange = useCallback(
		(field: "model" | "template", value: string) => {
			setPromptDraft((prev) => ({ ...prev, [field]: value }));
		},
		[],
	);
	const handleResetPrompt = useCallback(() => {
		setPromptDraft(promptBaseline);
		setPromptSaveError(null);
		setPromptRunError(null);
	}, [promptBaseline]);
	const handleSavePrompt = useCallback(async () => {
		if (!workPrompt?.id) {
			setPromptSaveError("Assign a prompt to this work before saving changes.");
			return;
		}
		if (!canOverridePrompt) {
			setPromptSaveError("Model and template are required.");
			return;
		}
		setPromptSaving(true);
		setPromptSaveError(null);
		try {
			await Prompts.appendPromptVersionPromptsPromptIdVersionsPost({
				path: { prompt_id: workPrompt.id },
				body: {
					model: promptDraft.model,
					template: promptDraft.template,
				},
				throwOnError: true,
			});
			setPromptBaseline({ ...promptDraft });
			setPromptDraft({ ...promptDraft });
			promptPristineRef.current = true;
			setPromptRunError(null);
			refreshWorkPrompt();
		} catch (error) {
			setPromptSaveError(
				getApiErrorMessage(
					error,
					"Failed to save prompt changes. Please try again.",
				),
			);
		} finally {
			setPromptSaving(false);
		}
	}, [canOverridePrompt, promptDraft, refreshWorkPrompt, workPrompt?.id]);

	const promptDrawer = useMemo(
		() => (
			<ChapterPromptDrawer
				trigger={
					<Button variant="outline" size="sm" disabled={workPromptLoading}>
						Edit Prompt
					</Button>
				}
				promptName={promptName}
				model={promptDraft.model}
				template={promptDraft.template}
				onModelChange={(value) => handlePromptDraftChange("model", value)}
				onTemplateChange={(value) => handlePromptDraftChange("template", value)}
				isDirty={isPromptDirty}
				isLoading={workPromptLoading}
				isSaving={promptSaving}
				onReset={handleResetPrompt}
				onSave={handleSavePrompt}
				saveDisabledReason={saveDisabledReason}
				errorMessage={promptSaveError}
				secondaryError={promptRunError}
				lastSavedAt={promptLastSavedAt}
				promptAssigned={Boolean(workPrompt) && !workPromptNotAssigned}
				workPromptError={workPromptError}
			/>
		),
		[
			handlePromptDraftChange,
			handleResetPrompt,
			handleSavePrompt,
			isPromptDirty,
			promptDraft.model,
			promptDraft.template,
			promptLastSavedAt,
			promptName,
			promptRunError,
			promptSaveError,
			promptSaving,
			saveDisabledReason,
			workPrompt,
			workPromptError,
			workPromptLoading,
			workPromptNotAssigned,
		],
	);

	const translationPanel = useMemo(
		() => (
			<TranslationPanel
				translationStatus={translationStatus}
				translationError={translationError}
				translationSegments={translationSegments}
				selectedSegmentId={selectedSegmentId}
				retranslatingSegmentId={retranslatingSegmentId}
				onContextSelect={handleSegmentContextSelect}
				onSegmentRetranslate={handleSegmentRetranslate}
				onClearSelection={handleClearSelection}
				primaryLabel={primaryLabel}
				primaryIcon={primaryIcon}
				primaryColorScheme={primaryColorScheme}
				isPrimaryLoading={isPrimaryLoading}
				onPrimaryAction={handlePrimaryAction}
				disablePrimary={disablePrimaryAction}
				isTranslationStreaming={isTranslationStreaming}
				promptRunError={promptRunError}
			/>
		),
		[
			handlePrimaryAction,
			handleClearSelection,
			handleSegmentContextSelect,
			handleSegmentRetranslate,
			isPrimaryLoading,
			isTranslationStreaming,
			primaryColorScheme,
			primaryIcon,
			primaryLabel,
			promptRunError,
			selectedSegmentId,
			translationError,
			translationSegments,
			translationStatus,
			retranslatingSegmentId,
			disablePrimaryAction,
		],
	);

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
							<Stack
								direction={{ base: "column", md: "row" }}
								gap={3}
								align={{ base: "flex-start", md: "center" }}
								justify="space-between"
								mb={4}
							>
								<Text color="gray.400" fontSize="sm">
									Sort key {chapter.sort_key.toFixed(4)}
								</Text>
								<HStack gap={2} flexWrap="wrap">
									{isPromptDirty ? (
										<Badge colorPalette="yellow">Using unsaved override</Badge>
									) : (
										<Badge colorPalette="gray">Using saved prompt</Badge>
									)}
									{workPromptNotAssigned ? (
										<Badge colorPalette="orange">
											Assign a prompt to save changes
										</Badge>
									) : null}
									{workPromptError ? (
										<Badge colorPalette="red">Prompt load failed</Badge>
									) : null}
									<Text fontSize="sm" color="gray.500">
										{workPromptLoading
											? "Loading prompt..."
											: promptName
												? `Prompt: ${promptName}`
												: workPromptNotAssigned
													? "No prompt assigned to this work."
													: "Prompt: Default system prompt"}
									</Text>
								</HStack>
								{promptDrawer}
							</Stack>

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

							{translationPanel}
						</Stack>
					</Stack>
				)}
			</Container>
		</Box>
	);
}

interface SegmentRowProps {
	segment: TranslationSegmentRow;
	isSelected: boolean;
	isRetranslating: boolean;
	onContextSelect: (segmentId: number) => void;
	onRetranslate: (segmentId: number) => void | Promise<void>;
}

interface TranslationPanelProps {
	translationStatus: TranslationStreamStatus;
	translationError: string | null;
	translationSegments: TranslationSegmentRow[];
	selectedSegmentId: number | null;
	retranslatingSegmentId: number | null;
	onContextSelect: (segmentId: number) => void;
	onSegmentRetranslate: (segmentId: number) => void | Promise<void>;
	onClearSelection: () => void;
	primaryLabel: string;
	primaryIcon: typeof Pause;
	primaryColorScheme: string;
	isPrimaryLoading: boolean;
	onPrimaryAction: () => void | Promise<void>;
	disablePrimary: boolean;
	isTranslationStreaming: boolean;
	promptRunError: string | null;
}

const TranslationPanel = memo(function TranslationPanel({
	translationStatus,
	translationError,
	translationSegments,
	selectedSegmentId,
	retranslatingSegmentId,
	onContextSelect,
	onSegmentRetranslate,
	onClearSelection,
	primaryLabel,
	primaryIcon,
	primaryColorScheme,
	isPrimaryLoading,
	onPrimaryAction,
	disablePrimary,
	isTranslationStreaming,
	promptRunError,
}: TranslationPanelProps) {
	return (
		<Box
			flex="1"
			w="full"
			borderWidth="1px"
			borderRadius="lg"
			px={6}
			pt={4}
			pb={6}
			onClick={onClearSelection}
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
						onClick={onPrimaryAction}
						loading={isPrimaryLoading}
						disabled={disablePrimary}
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
			{promptRunError ? (
				<Alert.Root status="error" borderRadius="md" mb={4}>
					<Alert.Indicator />
					<Alert.Content>
						<Alert.Description>{promptRunError}</Alert.Description>
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
				<Stack gap={5}>
					{translationSegments.map((segment) => (
						<SegmentRow
							key={segment.segmentId}
							segment={segment}
							isSelected={selectedSegmentId === segment.segmentId}
							isRetranslating={retranslatingSegmentId === segment.segmentId}
							onContextSelect={onContextSelect}
							onRetranslate={onSegmentRetranslate}
						/>
					))}
				</Stack>
			)}
		</Box>
	);
});

const SegmentRow = memo(function SegmentRow({
	segment,
	isSelected,
	isRetranslating,
	onContextSelect,
	onRetranslate,
}: SegmentRowProps) {
	const srcText = segment.src || "";
	const tgtText =
		segment.text || (segment.status === "running" ? "Translating..." : "");
	const hasSource = srcText.trim().length > 0;
	const hasTarget = tgtText.trim().length > 0;

	if (!hasSource && !hasTarget) {
		return <Box height="2" />;
	}

	return (
		<Menu.Root>
			<Menu.ContextTrigger
				w="full"
				bg={isSelected ? "blue.50" : "transparent"}
				borderRadius="md"
				p={3}
				borderWidth={isSelected ? "1px" : "0px"}
				borderColor={isSelected ? "blue.200" : "transparent"}
				cursor="context-menu"
				onContextMenu={() => onContextSelect(segment.segmentId)}
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
						<Text whiteSpace="pre-wrap" color="gray.400" textAlign="left">
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
							onClick={() => void onRetranslate(segment.segmentId)}
							disabled={isRetranslating}
						>
							{isRetranslating ? "Retranslating..." : "Retranslate Segment"}
						</Menu.Item>
					</Menu.Content>
				</Menu.Positioner>
			</Portal>
		</Menu.Root>
	);
});

async function parseErrorResponse(response: Response): Promise<string> {
	try {
		const data = (await response.json()) as { detail?: string };
		if (data?.detail && typeof data.detail === "string") {
			const trimmed = data.detail.trim();
			if (trimmed.length > 0) {
				return trimmed;
			}
		}
	} catch {
		// Ignore body parsing errors
	}
	return response.statusText || "Request failed";
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
