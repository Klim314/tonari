import type { QueryClient } from "@tanstack/react-query";
import {
	getChapterForWorkWorksWorkIdChaptersChapterIdGetQueryKey,
	getChapterTranslationStateWorksWorkIdChaptersChapterIdTranslationGetQueryKey,
	getPromptPromptsPromptIdGetQueryKey,
	getWorkPromptPromptsWorksWorkIdPromptGetQueryKey,
	getWorkWorksWorkIdGetQueryKey,
	listChapterGroupsWorksWorkIdChapterGroupsGetQueryKey,
	listChaptersForWorkWorksWorkIdChaptersGetQueryKey,
	listPromptsPromptsGetQueryKey,
	listPromptVersionsPromptsPromptIdVersionsGetQueryKey,
	listWorkPromptsPromptsWorksWorkIdPromptsGetQueryKey,
	searchWorksWorksGetQueryKey,
} from "../client/@tanstack/react-query.gen";

function getPromptVersionsQueryMatchKey(promptId: number) {
	return listPromptVersionsPromptsPromptIdVersionsGetQueryKey({
		path: { prompt_id: promptId },
	});
}

export function invalidatePromptLists(queryClient: QueryClient) {
	return queryClient.invalidateQueries({
		queryKey: listPromptsPromptsGetQueryKey(),
	});
}

export function invalidatePromptDetail(
	queryClient: QueryClient,
	promptId: number,
) {
	return queryClient.invalidateQueries({
		queryKey: getPromptPromptsPromptIdGetQueryKey({
			path: { prompt_id: promptId },
		}),
	});
}

export function invalidatePromptVersions(
	queryClient: QueryClient,
	promptId: number,
) {
	return queryClient.invalidateQueries({
		queryKey: getPromptVersionsQueryMatchKey(promptId),
	});
}

export function removePromptQueries(
	queryClient: QueryClient,
	promptId: number,
) {
	queryClient.removeQueries({
		queryKey: getPromptPromptsPromptIdGetQueryKey({
			path: { prompt_id: promptId },
		}),
	});
	queryClient.removeQueries({
		queryKey: getPromptVersionsQueryMatchKey(promptId),
	});
}

export function invalidateWorkPromptDetail(
	queryClient: QueryClient,
	workId: number,
) {
	return queryClient.invalidateQueries({
		queryKey: getWorkPromptPromptsWorksWorkIdPromptGetQueryKey({
			path: { work_id: workId },
		}),
	});
}

export function invalidateWorkPromptLists(
	queryClient: QueryClient,
	workId: number,
) {
	return queryClient.invalidateQueries({
		queryKey: listWorkPromptsPromptsWorksWorkIdPromptsGetQueryKey({
			path: { work_id: workId },
		}),
	});
}

export function invalidateWorkLists(queryClient: QueryClient) {
	return queryClient.invalidateQueries({
		queryKey: searchWorksWorksGetQueryKey(),
	});
}

export function invalidateWorkDetail(queryClient: QueryClient, workId: number) {
	return queryClient.invalidateQueries({
		queryKey: getWorkWorksWorkIdGetQueryKey({
			path: { work_id: workId },
		}),
	});
}

export function invalidateWorkChapters(
	queryClient: QueryClient,
	workId: number,
) {
	return Promise.all([
		queryClient.invalidateQueries({
			queryKey: listChaptersForWorkWorksWorkIdChaptersGetQueryKey({
				path: { work_id: workId },
			}),
		}),
		queryClient.invalidateQueries({
			queryKey: listChapterGroupsWorksWorkIdChapterGroupsGetQueryKey({
				path: { work_id: workId },
			}),
		}),
	]);
}

export function invalidateChapterDetail(
	queryClient: QueryClient,
	workId: number,
	chapterId: number,
) {
	return queryClient.invalidateQueries({
		queryKey: getChapterForWorkWorksWorkIdChaptersChapterIdGetQueryKey({
			path: {
				work_id: workId,
				chapter_id: chapterId,
			},
		}),
	});
}

export function invalidateChapterTranslation(
	queryClient: QueryClient,
	workId: number,
	chapterId: number,
) {
	return queryClient.invalidateQueries({
		queryKey:
			getChapterTranslationStateWorksWorkIdChaptersChapterIdTranslationGetQueryKey(
				{
					path: {
						work_id: workId,
						chapter_id: chapterId,
					},
				},
			),
	});
}
