import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { Prompts } from "../client";
import { getWorkPromptPromptsWorksWorkIdPromptGetQueryKey } from "../client/@tanstack/react-query.gen";
import { getApiErrorMessage } from "../lib/api";
import type { PromptDetail } from "../types/prompts";

export function useWorkPromptDetail(workId?: number | null) {
	const hasWorkId = workId != null;
	const query = useQuery<PromptDetail | null>({
		queryKey: hasWorkId
			? getWorkPromptPromptsWorksWorkIdPromptGetQueryKey({
					path: { work_id: workId },
				})
			: (["work-prompt", "empty", workId] as const),
		enabled: hasWorkId,
		queryFn: async ({ signal }) => {
			if (!hasWorkId) {
				return null;
			}

			try {
				const response = await Prompts.getWorkPromptPromptsWorksWorkIdPromptGet(
					{
						path: { work_id: workId },
						signal,
						throwOnError: true,
					},
				);
				return response.data;
			} catch (queryError) {
				if (
					axios.isAxiosError(queryError) &&
					queryError.response?.status === 404
				) {
					return null;
				}
				throw queryError;
			}
		},
	});

	return {
		data: query.data ?? null,
		loading: query.isLoading,
		error: query.error
			? getApiErrorMessage(
					query.error,
					"Failed to load the prompt assigned to this work.",
				)
			: null,
		notAssigned: hasWorkId && !query.isLoading && !query.error && !query.data,
	};
}
