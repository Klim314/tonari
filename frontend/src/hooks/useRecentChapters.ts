import {
	listRecentChaptersWorksRecentChaptersGetOptions,
	listRecentChaptersWorksRecentChaptersGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import type { RecentChapterOut } from "../client/types.gen";
import { useQueryState } from "../lib/queryState";

const DEFAULT_LIMIT = 5;

export function useRecentChapters(limit: number = DEFAULT_LIMIT) {
	const { data, loading, error } = useQueryState<
		RecentChapterOut[],
		RecentChapterOut[],
		Error,
		ReturnType<typeof listRecentChaptersWorksRecentChaptersGetQueryKey>
	>({
		...listRecentChaptersWorksRecentChaptersGetOptions({
			query: { limit },
		}),
		fallbackErrorMessage: "Failed to fetch recently read chapters",
	});

	return { data, loading, error };
}
