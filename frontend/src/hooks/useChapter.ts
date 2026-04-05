import {
	getChapterForWorkWorksWorkIdChaptersChapterIdGetOptions,
	getChapterForWorkWorksWorkIdChaptersChapterIdGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { ChapterDetail } from "../types/works";

export function useChapter(
	workId: number | null | undefined,
	chapterId: number | null | undefined,
) {
	const hasIds = workId != null && chapterId != null;
	const { data, loading, error } = useQueryState<
		ChapterDetail,
		ChapterDetail,
		Error,
		ReturnType<typeof getChapterForWorkWorksWorkIdChaptersChapterIdGetQueryKey>
	>({
		...getChapterForWorkWorksWorkIdChaptersChapterIdGetOptions({
			path: {
				work_id: workId ?? 0,
				chapter_id: chapterId ?? 0,
			},
		}),
		enabled: hasIds,
		fallbackErrorMessage: "Failed to fetch chapter",
	});

	return { data, loading, error };
}
