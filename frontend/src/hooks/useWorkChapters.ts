import { keepPreviousData } from "@tanstack/react-query";
import {
	listChaptersForWorkWorksWorkIdChaptersGetOptions,
	listChaptersForWorkWorksWorkIdChaptersGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { PaginatedChaptersResponse } from "../types/works";

export function useWorkChapters(
	workId: number | null | undefined,
	limit: number,
	offset: number,
) {
	const hasWorkId = workId != null;
	const { data, loading, error } = useQueryState<
		PaginatedChaptersResponse,
		PaginatedChaptersResponse,
		Error,
		ReturnType<typeof listChaptersForWorkWorksWorkIdChaptersGetQueryKey>
	>({
		...listChaptersForWorkWorksWorkIdChaptersGetOptions({
			path: { work_id: workId ?? 0 },
			query: { limit, offset },
		}),
		enabled: hasWorkId,
		placeholderData: keepPreviousData,
		fallbackErrorMessage: "Failed to fetch chapters",
	});

	return { data, loading, error };
}
