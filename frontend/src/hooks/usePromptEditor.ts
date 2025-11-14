import { useCallback, useRef } from "react";
import type { PromptEditorHandle } from "../components/PromptEditor";

export function usePromptEditor() {
	const handleRef = useRef<PromptEditorHandle | null>(null);

	const registerEditor = useCallback((handle: PromptEditorHandle | null) => {
		handleRef.current = handle;
	}, []);

	const saveChanges = useCallback(async () => {
		if (!handleRef.current) {
			return;
		}
		await handleRef.current.saveChanges();
	}, []);

	const discardChanges = useCallback(() => {
		handleRef.current?.discardChanges();
	}, []);

	return {
		registerEditor,
		saveChanges,
		discardChanges,
	};
}
