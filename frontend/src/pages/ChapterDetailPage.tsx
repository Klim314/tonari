import { Button } from "@chakra-ui/react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ChapterPromptDrawer } from "../components/ChapterPromptDrawer";
import { ChapterDetailView } from "../components/chapterDetail/ChapterDetailView";
import type { TranslationPanelProps } from "../components/chapterDetail/translation/TranslationPanel";
import type { PromptMeta } from "../components/chapterDetail/types";
import { useChapter } from "../hooks/useChapter";
import { useChapterTranslationStream } from "../hooks/useChapterTranslationStream";
import { usePromptOverride } from "../hooks/usePromptOverride";
import { useWork } from "../hooks/useWork";
import { useWorkPromptDetail } from "../hooks/useWorkPromptDetail";
import { regenerateChapterSegments } from "../lib/chapters";

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

	const promptOverride = usePromptOverride({
		workPrompt,
		workPromptNotAssigned,
		onRefresh: refreshWorkPrompt,
	});

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

	const startTranslationRun = useCallback(() => {
		startTranslation();
	}, [startTranslation]);

	const handleRegenerate = useCallback(async () => {
		const ok = await regenerateTranslation();
		if (ok) {
			startTranslationRun();
		}
	}, [regenerateTranslation, startTranslationRun]);

	const handlePrimaryAction = useCallback(async () => {
		if (isTranslationStreaming) {
			pauseTranslation();
			return;
		}
		if (primaryAction === "regenerate") {
			await handleRegenerate();
			return;
		}
		startTranslationRun();
	}, [
		handleRegenerate,
		isTranslationStreaming,
		pauseTranslation,
		primaryAction,
		startTranslationRun,
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

	const disablePrimaryAction = !isTranslationStreaming && (!work || !chapter);

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

	const handleRegenerateSegments = useCallback(async () => {
		if (!workId || !chapterId) return;
		setIsRegeneratingSegments(true);
		try {
			await regenerateChapterSegments(workId, chapterId);
			await regenerateTranslation();
		} catch (error) {
			console.error("Error regenerating segments:", error);
		} finally {
			setIsRegeneratingSegments(false);
		}
	}, [chapterId, regenerateTranslation, workId]);

	const promptDrawerTrigger = (
		<ChapterPromptDrawer
			trigger={
				<Button variant="outline" size="sm" disabled={workPromptLoading}>
					Edit Prompt
				</Button>
			}
			promptName={promptOverride.promptName}
			model={promptOverride.draft.model}
			template={promptOverride.draft.template}
			onModelChange={(value) =>
				promptOverride.handleDraftChange("model", value)
			}
			onTemplateChange={(value) =>
				promptOverride.handleDraftChange("template", value)
			}
			isDirty={promptOverride.isDirty}
			isLoading={workPromptLoading}
			isSaving={promptOverride.saving}
			onReset={promptOverride.resetDraft}
			onSave={promptOverride.saveDraft}
			saveDisabledReason={promptOverride.saveDisabledReason}
			errorMessage={promptOverride.error}
			lastSavedAt={promptOverride.lastSavedAt}
			promptAssigned={promptOverride.promptAssigned}
			workPromptError={workPromptError}
		/>
	);

	const translationPanelProps: TranslationPanelProps = {
		translationStatus,
		translationError,
		translationSegments,
		selectedSegmentId,
		retranslatingSegmentId,
		onContextSelect: handleSegmentContextSelect,
		onSegmentRetranslate: handleSegmentRetranslate,
		onClearSelection: handleClearSelection,
		primaryLabel,
		primaryIcon,
		primaryColorScheme,
		isPrimaryLoading,
		onPrimaryAction: handlePrimaryAction,
		disablePrimary: disablePrimaryAction,
	};

	const promptMeta: PromptMeta = {
		isDirty: promptOverride.isDirty,
		loading: workPromptLoading,
		notAssigned: workPromptNotAssigned,
		error: workPromptError,
		promptName: promptOverride.promptName,
	};

	const loading = workLoading || chapterLoading;
	const error = workError || chapterError;

	return (
		<ChapterDetailView
			work={work ?? null}
			chapter={chapter ?? null}
			promptMeta={promptMeta}
			promptDrawerTrigger={promptDrawerTrigger}
			translationPanelProps={translationPanelProps}
			onNavigateBack={() => onNavigateBack(`/works/${workId}`)}
			onRegenerateSegments={handleRegenerateSegments}
			isRegeneratingSegments={isRegeneratingSegments}
			isLoading={loading}
			errorMessage={error}
		/>
	);
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
