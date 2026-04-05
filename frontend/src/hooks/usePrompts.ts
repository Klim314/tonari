import { keepPreviousData } from "@tanstack/react-query";
import {
	listPromptsPromptsGetOptions,
	listPromptsPromptsGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { PaginatedPromptsResponse } from "../types/prompts";
import { useDebouncedValue } from "./useDebouncedValue";

const SEARCH_DEBOUNCE_MS = 300;

export function usePrompts(searchQuery: string) {
	const debouncedQuery = useDebouncedValue(
		searchQuery.trim(),
		SEARCH_DEBOUNCE_MS,
	);

	const { data, loading, error } = useQueryState<
		PaginatedPromptsResponse,
		PaginatedPromptsResponse,
		Error,
		ReturnType<typeof listPromptsPromptsGetQueryKey>
	>({
		...listPromptsPromptsGetOptions({
			query: {
				limit: 50,
				offset: 0,
				q: debouncedQuery || undefined,
			},
		}),
		placeholderData: keepPreviousData,
		fallbackErrorMessage: "Failed to fetch prompts",
	});

	return { data, loading, error };
}
