import {
	listModelsModelsGetOptions,
	listModelsModelsGetQueryKey,
} from "../client/@tanstack/react-query.gen";
import type { ListModelsModelsGetResponse } from "../client/types.gen";
import { useQueryState } from "../lib/queryState";

export function useModels() {
	const { data, loading, error } = useQueryState<
		ListModelsModelsGetResponse,
		string[],
		Error,
		ReturnType<typeof listModelsModelsGetQueryKey>
	>({
		...listModelsModelsGetOptions(),
		select: (response) => response.items?.map((model) => model.id) ?? [],
		emptyData: [],
		fallbackErrorMessage: "Failed to fetch models",
	});

	return { data: data ?? [], loading, error };
}
