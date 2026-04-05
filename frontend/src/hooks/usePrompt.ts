import {
	getPromptPromptsPromptIdGetOptions,
	getPromptPromptsPromptIdGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { PromptDetail } from "../types/prompts";

export function usePrompt(promptId: number | null) {
	const hasPromptId = promptId != null;
	const { data, loading, error } = useQueryState<
		PromptDetail,
		PromptDetail,
		Error,
		ReturnType<typeof getPromptPromptsPromptIdGetQueryKey>
	>({
		...getPromptPromptsPromptIdGetOptions({
			path: { prompt_id: promptId ?? 0 },
		}),
		enabled: hasPromptId,
		fallbackErrorMessage: "Failed to fetch prompt",
	});

	return { data, loading, error };
}
