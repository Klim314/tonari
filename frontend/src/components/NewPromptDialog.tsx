import {
	Box,
	Button,
	DialogBackdrop,
	DialogBody,
	DialogCloseTrigger,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogPositioner,
	DialogRoot,
	DialogTitle,
	HStack,
	Stack,
	Text,
} from "@chakra-ui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { PromptOut } from "../client";
import {
	appendPromptVersionPromptsPromptIdVersionsPostMutation,
	createPromptPromptsPostMutation,
	getWorkPromptPromptsWorksWorkIdPromptGetQueryKey,
	updateWorkPromptPromptsWorksWorkIdPromptPatchMutation,
} from "../client/@tanstack/react-query.gen";
import { getApiErrorMessage } from "../lib/api";
import {
	invalidatePromptLists,
	invalidateWorkPromptDetail,
	invalidateWorkPromptLists,
} from "../lib/queryInvalidation";
import { MetadataEditor } from "./PromptEditor/MetadataEditor";
import { TemplateEditor } from "./PromptEditor/TemplateEditor";

interface NewPromptDialogProps {
	isOpen: boolean;
	onClose: () => void;
	workId: number;
	onCreated?: (prompt: PromptOut) => void;
}

interface Draft {
	name: string;
	description: string;
	model: string;
	template: string;
}

const emptyDraft: Draft = {
	name: "",
	description: "",
	model: "",
	template: "",
};

export function NewPromptDialog({
	isOpen,
	onClose,
	workId,
	onCreated,
}: NewPromptDialogProps) {
	const queryClient = useQueryClient();
	const [draft, setDraft] = useState<Draft>(emptyDraft);
	const [error, setError] = useState<string | null>(null);
	const [isSaving, setIsSaving] = useState(false);

	const createPrompt = useMutation({
		...createPromptPromptsPostMutation(),
	});
	const appendVersion = useMutation({
		...appendPromptVersionPromptsPromptIdVersionsPostMutation(),
	});
	const assignPrompt = useMutation({
		...updateWorkPromptPromptsWorksWorkIdPromptPatchMutation(),
	});

	useEffect(() => {
		if (isOpen) {
			setDraft(emptyDraft);
			setError(null);
		}
	}, [isOpen]);

	const updateField = (field: keyof Draft, value: string) => {
		setDraft((prev) => ({ ...prev, [field]: value }));
	};

	const canSave =
		draft.name.trim().length > 0 &&
		draft.model.trim().length > 0 &&
		draft.template.trim().length > 0 &&
		!isSaving;

	const handleSave = async () => {
		if (!canSave) return;

		setIsSaving(true);
		setError(null);
		try {
			const created = await createPrompt.mutateAsync({
				body: {
					name: draft.name.trim(),
					description: draft.description.trim() || null,
				},
			});

			await appendVersion.mutateAsync({
				path: { prompt_id: created.id },
				body: {
					model: draft.model.trim(),
					template: draft.template,
				},
			});

			const assigned = await assignPrompt.mutateAsync({
				path: { work_id: workId },
				body: { prompt_id: created.id },
			});

			queryClient.setQueryData(
				getWorkPromptPromptsWorksWorkIdPromptGetQueryKey({
					path: { work_id: workId },
				}),
				assigned,
			);
			await Promise.all([
				invalidatePromptLists(queryClient),
				invalidateWorkPromptDetail(queryClient, workId),
				invalidateWorkPromptLists(queryClient, workId),
			]);

			onCreated?.(assigned);
			onClose();
		} catch (err) {
			setError(getApiErrorMessage(err, "Failed to create prompt"));
		} finally {
			setIsSaving(false);
		}
	};

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(event) => {
				if (!event.open && !isSaving) onClose();
			}}
			trapFocus
			motionPreset="scale"
			size="xl"
		>
			<DialogBackdrop bg="blackAlpha.600" />
			<DialogPositioner>
				<DialogContent>
					<DialogCloseTrigger />
					<DialogHeader>
						<DialogTitle>New Prompt</DialogTitle>
					</DialogHeader>
					<DialogBody>
						<Stack gap={6}>
							<MetadataEditor
								name={draft.name}
								description={draft.description}
								onNameChange={(name) => updateField("name", name)}
								onDescriptionChange={(description) =>
									updateField("description", description)
								}
								autoEditName
							/>
							<TemplateEditor
								model={draft.model}
								template={draft.template}
								onModelChange={(model) => updateField("model", model)}
								onTemplateChange={(template) =>
									updateField("template", template)
								}
							/>
							{error && (
								<Box
									p={3}
									borderRadius="md"
									bg="red.900"
									borderLeftWidth="4px"
									borderLeftColor="red.400"
								>
									<Text fontSize="sm" color="red.100">
										{error}
									</Text>
								</Box>
							)}
						</Stack>
					</DialogBody>
					<DialogFooter>
						<HStack gap={2}>
							<Button variant="ghost" onClick={onClose} disabled={isSaving}>
								Cancel
							</Button>
							<Button
								colorScheme="blue"
								onClick={handleSave}
								disabled={!canSave}
								loading={isSaving}
							>
								Create &amp; Assign
							</Button>
						</HStack>
					</DialogFooter>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}
