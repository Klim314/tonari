import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Prompts } from "../client";
import { getApiErrorMessage } from "../lib/api";
import type { PromptDetail } from "../types/prompts";

interface UsePromptOverrideOptions {
	workPrompt: PromptDetail | null;
	workPromptNotAssigned: boolean;
	onRefresh?: () => void;
}

interface PromptDraft {
	model: string;
	template: string;
}

export interface PromptOverrideController {
	draft: PromptDraft;
	baseline: PromptDraft;
	isDirty: boolean;
	canSave: boolean;
	saving: boolean;
	error: string | null;
	saveDisabledReason: string | null;
	promptName?: string;
	promptAssigned: boolean;
	lastSavedAt: Date | null;
	handleDraftChange: (field: keyof PromptDraft, value: string) => void;
	resetDraft: () => void;
	saveDraft: () => Promise<void>;
}

const emptyDraft: PromptDraft = { model: "", template: "" };

export function usePromptOverride({
	workPrompt,
	workPromptNotAssigned,
	onRefresh,
}: UsePromptOverrideOptions): PromptOverrideController {
	const [draft, setDraft] = useState<PromptDraft>(emptyDraft);
	const [baseline, setBaseline] = useState<PromptDraft>(emptyDraft);
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const promptPristineRef = useRef(true);

	useEffect(() => {
		const latestModel = workPrompt?.latest_version?.model ?? "";
		const latestTemplate = workPrompt?.latest_version?.template ?? "";
		const nextBaseline = { model: latestModel, template: latestTemplate };
		setBaseline(nextBaseline);
		if (promptPristineRef.current) {
			setDraft(nextBaseline);
			setError(null);
		}
	}, [workPrompt]);

	const isDirty =
		draft.model !== baseline.model || draft.template !== baseline.template;

	useEffect(() => {
		promptPristineRef.current = !isDirty;
	}, [isDirty]);

	const promptAssigned = Boolean(workPrompt) && !workPromptNotAssigned;
	const canSave =
		promptAssigned &&
		draft.model.trim().length > 0 &&
		draft.template.trim().length > 0;

	const saveDisabledReason = useMemo(() => {
		if (!promptAssigned) {
			return "Assign a prompt to this work before saving changes.";
		}
		if (isDirty && !canSave) {
			return "Model and template are required.";
		}
		return null;
	}, [canSave, isDirty, promptAssigned]);

	const handleDraftChange = useCallback(
		(field: keyof PromptDraft, value: string) => {
			setDraft((prev) => ({ ...prev, [field]: value }));
		},
		[],
	);

	const resetDraft = useCallback(() => {
		setDraft(baseline);
		setError(null);
		promptPristineRef.current = true;
	}, [baseline]);

	const saveDraft = useCallback(async () => {
		if (!workPrompt?.id) {
			setError("Assign a prompt to this work before saving changes.");
			return;
		}
		if (!canSave) {
			setError("Model and template are required.");
			return;
		}
		setSaving(true);
		setError(null);
		try {
			await Prompts.appendPromptVersionPromptsPromptIdVersionsPost({
				path: { prompt_id: workPrompt.id },
				body: { model: draft.model, template: draft.template },
				throwOnError: true,
			});
			setBaseline(draft);
			promptPristineRef.current = true;
			onRefresh?.();
		} catch (err) {
			setError(
				getApiErrorMessage(
					err,
					"Failed to save prompt changes. Please try again.",
				),
			);
		} finally {
			setSaving(false);
		}
	}, [canSave, draft, onRefresh, workPrompt?.id]);

	const promptName = workPrompt?.name ?? undefined;
	const lastSavedAt = workPrompt?.latest_version?.created_at
		? new Date(workPrompt.latest_version.created_at)
		: null;

	return {
		draft,
		baseline,
		isDirty,
		canSave,
		saving,
		error,
		saveDisabledReason,
		promptName,
		promptAssigned,
		lastSavedAt,
		handleDraftChange,
		resetDraft,
		saveDraft,
	};
}
