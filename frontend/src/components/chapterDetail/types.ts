import type { ChapterTranslationSegment } from "../../hooks/useChapterTranslationStream";

export interface PromptMeta {
	isDirty: boolean;
	loading: boolean;
	notAssigned: boolean;
	error: string | null;
	promptName?: string;
}

export type TranslationSegmentRow = ChapterTranslationSegment;
