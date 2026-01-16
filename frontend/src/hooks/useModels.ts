import { useEffect, useState } from "react";
import { Models } from "../client";
import { getApiErrorMessage } from "../lib/api";

interface ModelsState {
	data: string[];
	loading: boolean;
	error: string | null;
}

const defaultState: ModelsState = {
	data: [],
	loading: false,
	error: null,
};

export function useModels() {
	const [state, setState] = useState<ModelsState>(defaultState);

	useEffect(() => {
		let cancelled = false;

		async function fetchModels() {
			setState((prev) => ({ ...prev, loading: true, error: null }));
			try {
				const response = await Models.listModelsModelsGet({
					throwOnError: true,
				});

				if (!cancelled) {
					// response.data is ModelsListOut, which has items: ModelInfoOut[]
					const modelIds = response.data?.items?.map((m) => m.id) || [];
					setState({
						data: modelIds,
						loading: false,
						error: null,
					});
				}
			} catch (error) {
				if (cancelled) return;
				setState({
					data: [],
					loading: false,
					error: getApiErrorMessage(error, "Failed to fetch models"),
				});
			}
		}

		fetchModels();

		return () => {
			cancelled = true;
		};
	}, []);

	return state;
}
