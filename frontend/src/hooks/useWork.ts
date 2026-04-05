import {
	getWorkWorksWorkIdGetOptions,
	getWorkWorksWorkIdGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import { useQueryState } from "../lib/queryState";
import type { Work } from "../types/works";

export function useWork(workId?: number | null) {
	const hasWorkId = workId != null;
	const { data, loading, error } = useQueryState<
		Work,
		Work,
		Error,
		ReturnType<typeof getWorkWorksWorkIdGetQueryKey>
	>({
		...getWorkWorksWorkIdGetOptions({
			path: { work_id: workId ?? 0 },
		}),
		enabled: hasWorkId,
		fallbackErrorMessage: "Failed to fetch work",
	});

	return { data, loading, error };
}
