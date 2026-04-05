import { keepPreviousData } from "@tanstack/react-query";
import {
	searchWorksWorksGetOptions,
	searchWorksWorksGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { PaginatedWorksResponse } from "../types/works";
import { useDebouncedValue } from "./useDebouncedValue";

const SEARCH_DEBOUNCE_MS = 300;

export function useWorks(searchQuery: string) {
	const debouncedQuery = useDebouncedValue(
		searchQuery.trim(),
		SEARCH_DEBOUNCE_MS,
	);

	const { data, loading, error } = useQueryState<
		PaginatedWorksResponse,
		PaginatedWorksResponse,
		Error,
		ReturnType<typeof searchWorksWorksGetQueryKey>
	>({
		...searchWorksWorksGetOptions({
			query: {
				limit: 50,
				offset: 0,
				q: debouncedQuery || undefined,
			},
		}),
		placeholderData: keepPreviousData,
		fallbackErrorMessage: "Failed to fetch works",
	});

	return { data, loading, error };
}
