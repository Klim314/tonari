import {
	type QueryKey,
	type UseQueryOptions,
	useQuery,
} from "@tanstack/react-query";
import { getApiErrorMessage } from "./api";

interface QueryStateOptions<
	TQueryFnData,
	TData = TQueryFnData,
	TError = unknown,
	TQueryKey extends QueryKey = QueryKey,
> extends UseQueryOptions<TQueryFnData, TError, TData, TQueryKey> {
	fallbackErrorMessage: string;
	emptyData?: TData | null;
}

export function useQueryState<
	TQueryFnData,
	TData = TQueryFnData,
	TError = unknown,
	TQueryKey extends QueryKey = QueryKey,
>({
	fallbackErrorMessage,
	emptyData = null,
	...options
}: QueryStateOptions<TQueryFnData, TData, TError, TQueryKey>) {
	const query = useQuery(options);

	return {
		query,
		data: (query.data ?? emptyData) as TData | null,
		loading: query.isLoading,
		error: query.error
			? getApiErrorMessage(query.error, fallbackErrorMessage)
			: null,
	};
}
