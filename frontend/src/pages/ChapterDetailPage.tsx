import { Button } from "@chakra-ui/react";
import { useCallback, useState } from "react";
import { ChapterPromptDrawer } from "../components/ChapterPromptDrawer";
import { ChapterDetailView } from "../components/chapterDetail/ChapterDetailView";
import type { TranslationPanelProps } from "../components/chapterDetail/translation/TranslationPanel";
import type { PromptMeta } from "../components/chapterDetail/types";
import { useChapter } from "../hooks/useChapter";
import { usePromptOverride } from "../hooks/usePromptOverride";
import { useWork } from "../hooks/useWork";
import { useWorkPromptDetail } from "../hooks/useWorkPromptDetail";
import { regenerateChapterSegments } from "../lib/chapters";

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
	const [translationRefreshKey, setTranslationRefreshKey] = useState(0);

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

	const handleRegenerateSegments = useCallback(async () => {
		if (!workId || !chapterId) return;
		setIsRegeneratingSegments(true);
		try {
			await regenerateChapterSegments(workId, chapterId);
			setTranslationRefreshKey((key) => key + 1);
		} catch (error) {
			console.error("Error regenerating segments:", error);
		} finally {
			setIsRegeneratingSegments(false);
		}
	}, [chapterId, workId]);

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
		workId,
		chapterId,
		refreshKey: translationRefreshKey,
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
