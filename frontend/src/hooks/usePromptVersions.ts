import {
	listPromptVersionsPromptsPromptIdVersionsGetOptions,
	listPromptVersionsPromptsPromptIdVersionsGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { PaginatedPromptVersionsResponse } from "../types/prompts";

export function usePromptVersions(promptId: number | null) {
	const hasPromptId = promptId != null;
	const { data, loading, error } = useQueryState<
		PaginatedPromptVersionsResponse,
		PaginatedPromptVersionsResponse,
		Error,
		ReturnType<typeof listPromptVersionsPromptsPromptIdVersionsGetQueryKey>
	>({
		...listPromptVersionsPromptsPromptIdVersionsGetOptions({
			path: { prompt_id: promptId ?? 0 },
			query: {
				limit: 50,
				offset: 0,
			},
		}),
		enabled: hasPromptId,
		fallbackErrorMessage: "Failed to fetch prompt versions",
	});

	return { data, loading, error };
}
