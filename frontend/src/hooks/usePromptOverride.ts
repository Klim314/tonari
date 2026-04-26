import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { appendPromptVersionPromptsPromptIdVersionsPostMutation } from "../client/@tanstack/react-query.gen";
import { getApiErrorMessage } from "../lib/api";
import {
	invalidatePromptDetail,
	invalidatePromptVersions,
	invalidateWorkPromptDetail,
} from "../lib/queryInvalidation";
import type { PromptDetail } from "../types/prompts";

interface UsePromptOverrideOptions {
	workId?: number | null;
	workPrompt: PromptDetail | null;
	workPromptNotAssigned: boolean;
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
	workId,
	workPrompt,
	workPromptNotAssigned,
}: UsePromptOverrideOptions): PromptOverrideController {
	const queryClient = useQueryClient();
	const [draft, setDraft] = useState<PromptDraft>(emptyDraft);
	const [baseline, setBaseline] = useState<PromptDraft>(emptyDraft);
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const promptPristineRef = useRef(true);
	const appendPromptVersion = useMutation({
		...appendPromptVersionPromptsPromptIdVersionsPostMutation(),
	});

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
	const canSave = promptAssigned && draft.model.trim().length > 0;

	const saveDisabledReason = useMemo(() => {
		if (!promptAssigned) {
			return "Assign a prompt to this work before saving changes.";
		}
		if (isDirty && !canSave) {
			return "Model is required.";
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
			setError("Model is required.");
			return;
		}
		setSaving(true);
		setError(null);
		try {
			await appendPromptVersion.mutateAsync({
				path: { prompt_id: workPrompt.id },
				body: { model: draft.model, template: draft.template },
			});
			await Promise.all([
				invalidatePromptDetail(queryClient, workPrompt.id),
				invalidatePromptVersions(queryClient, workPrompt.id),
				...(workId ? [invalidateWorkPromptDetail(queryClient, workId)] : []),
			]);
			setBaseline(draft);
			promptPristineRef.current = true;
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
	}, [appendPromptVersion, canSave, draft, queryClient, workId, workPrompt]);

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
