import { useEffect, useState } from "react";

const STORAGE_KEY = "explanation_v2";
const URL_PARAM = "explanation_v2";

function readStored(): boolean {
	if (typeof window === "undefined") return false;
	return window.localStorage.getItem(STORAGE_KEY) === "1";
}

function syncFromUrl(): boolean | null {
	if (typeof window === "undefined") return null;
	const params = new URLSearchParams(window.location.search);
	if (!params.has(URL_PARAM)) return null;
	const value = params.get(URL_PARAM) === "1";
	window.localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
	return value;
}

export function useExplanationV2Flag(): boolean {
	const [enabled, setEnabled] = useState<boolean>(() => {
		const fromUrl = syncFromUrl();
		return fromUrl ?? readStored();
	});

	useEffect(() => {
		const onStorage = (event: StorageEvent) => {
			if (event.key === STORAGE_KEY) {
				setEnabled(event.newValue === "1");
			}
		};
		window.addEventListener("storage", onStorage);
		return () => window.removeEventListener("storage", onStorage);
	}, []);

	return enabled;
}
