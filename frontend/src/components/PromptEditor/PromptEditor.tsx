import { useEffect, useState, useCallback } from "react";
import {
	Box,
	Button,
	Container,
	Stack,
	Text,
	Skeleton,
	HStack,
	VStack,
	useDisclosure,
} from "@chakra-ui/react";
import { ChevronLeft } from "lucide-react";
import { usePrompt } from "../../hooks/usePrompt";
import { usePromptVersions } from "../../hooks/usePromptVersions";
import { MetadataEditor } from "./MetadataEditor";
import { TemplateEditor } from "./TemplateEditor";
import { VersionHistory } from "./VersionHistory";
import { UnsavedChangesDialog } from "./UnsavedChangesDialog";
import { Prompts } from "../../client";

export interface EditorDraft {
	name: string;
	description: string;
	model: string;
	template: string;
}


export interface PromptEditorState {
	promptId: number;
	draft: EditorDraft;
	isDirty: boolean;
	isSaving: boolean;
	lastSaveTime: Date | null;
	selectedVersionId: number | null;
}

export interface PromptEditorHandle {
	saveChanges: () => Promise<void>;
	discardChanges: () => void;
}

interface PromptEditorProps {
	promptId: number | null;
	variant?: "page" | "embedded";
	onDirtyChange?: (dirty: boolean) => void;
	onPromptSaved?: () => void;
	onRequestNavigate?: (path: string) => void;
	showVersionSidebar?: boolean;
	onSavingChange?: (saving: boolean) => void;
	onRegisterEditor?: (handle: PromptEditorHandle | null) => void;
}

const emptyDraft: EditorDraft = {
	name: "",
	description: "",
	model: "",
	template: "",
};

export function PromptEditor({
	promptId,
	variant = "page",
	onDirtyChange,
	onPromptSaved,
	onRequestNavigate,
	showVersionSidebar = true,
	onSavingChange,
	onRegisterEditor,
}: PromptEditorProps) {
	const { open: isOpen, onOpen, onClose } = useDisclosure();
	const [pendingNavigation, setPendingNavigation] = useState<string | null>(
		null,
	);

	const resolvedPromptId = promptId;
	const [refreshToken, setRefreshToken] = useState(0);

	const promptState = usePrompt(resolvedPromptId, refreshToken);
	const versionsState = usePromptVersions(resolvedPromptId, refreshToken);

	const [editorState, setEditorState] = useState<PromptEditorState>({
		promptId: resolvedPromptId || 0,
		draft: emptyDraft,
		isDirty: false,
		isSaving: false,
		lastSaveTime: null,
		selectedVersionId: null,
	});

	// Reset local editor state when prompt id changes
	useEffect(() => {
		setEditorState({
			promptId: resolvedPromptId || 0,
			draft: emptyDraft,
			isDirty: false,
			isSaving: false,
			lastSaveTime: null,
			selectedVersionId: null,
		});
	}, [resolvedPromptId]);

	// Initialize draft from loaded prompt
	useEffect(() => {
		if (promptState.data) {
			const latestVersion = promptState.data.latest_version;
			setEditorState((prev) => ({
				...prev,
				draft: {
					name: promptState.data!.name,
					description: promptState.data!.description || "",
					model: latestVersion?.model || "",
					template: latestVersion?.template || "",
				},
			}));
		}
	}, [promptState.data]);

	useEffect(() => {
		onDirtyChange?.(editorState.isDirty);
	}, [editorState.isDirty, onDirtyChange]);

	useEffect(() => {
		onSavingChange?.(editorState.isSaving);
	}, [editorState.isSaving, onSavingChange]);

	const handleDraftChange = useCallback(
		(field: keyof EditorDraft, value: string) => {
			setEditorState((prev) => ({
				...prev,
				draft: {
					...prev.draft,
					[field]: value,
				},
				isDirty: true,
			}));
		},
		[],
	);

	const handleSelectVersion = useCallback((versionId: number) => {
		setEditorState((prev) => ({
			...prev,
			selectedVersionId: versionId,
		}));

		// Load the selected version's template and model into view
		// (not into draft - just for viewing)
	}, []);

	const handleSaveChanges = useCallback(async () => {
		if (!resolvedPromptId || editorState.isSaving) return;

		setEditorState((prev) => ({
			...prev,
			isSaving: true,
		}));

		try {
			// First, update metadata (name, description)
			await Prompts.updatePromptPromptsPromptIdPatch({
				path: { prompt_id: resolvedPromptId },
				body: {
					name: editorState.draft.name,
					description: editorState.draft.description || null,
				},
				throwOnError: true,
			});

			// Then, create or update version
			// TODO: Backend will handle 5-min window logic
			await Prompts.appendPromptVersionPromptsPromptIdVersionsPost({
				path: { prompt_id: resolvedPromptId },
				body: {
					model: editorState.draft.model,
					template: editorState.draft.template,
				},
				throwOnError: true,
			});

			setEditorState((prev) => ({
				...prev,
				isDirty: false,
				isSaving: false,
				lastSaveTime: new Date(),
				selectedVersionId: null,
			}));

			setRefreshToken((prev) => prev + 1);
			onPromptSaved?.();
		} catch (error) {
			console.error("Failed to save changes:", error);
			setEditorState((prev) => ({
				...prev,
				isSaving: false,
			}));
		}
	}, [editorState.draft.description, editorState.draft.model, editorState.draft.name, editorState.draft.template, editorState.isSaving, onPromptSaved, resolvedPromptId]);

	const handleDiscardChanges = useCallback(() => {
		// Reset draft to last saved state
		if (promptState.data) {
			const latestVersion = promptState.data.latest_version;
			setEditorState((prev) => ({
				...prev,
				draft: {
					name: promptState.data!.name,
					description: promptState.data!.description || "",
					model: latestVersion?.model || "",
					template: latestVersion?.template || "",
				},
				isDirty: false,
				selectedVersionId: null,
			}));
		}
	}, [promptState.data]);

	const handleNavigateAway = useCallback(
		(path: string) => {
			if (editorState.isDirty) {
				setPendingNavigation(path);
				onOpen();
			} else {
				onRequestNavigate?.(path);
			}
		},
		[editorState.isDirty, onOpen, onRequestNavigate],
	);

	const handleConfirmDiscard = () => {
		onClose();
		if (pendingNavigation) {
			onRequestNavigate?.(pendingNavigation);
		}
	};

	const handleConfirmSave = async () => {
		await handleSaveChanges();
		onClose();
		if (pendingNavigation) {
			onRequestNavigate?.(pendingNavigation);
		}
	};

	const isLoading = promptState.loading || versionsState.loading;
	const hasError = promptState.error || versionsState.error;
	const latestVersion = promptState.data?.latest_version;

	useEffect(() => {
		if (!onRegisterEditor) {
			return;
		}

		const handle: PromptEditorHandle = {
			saveChanges: handleSaveChanges,
			discardChanges: handleDiscardChanges,
		};

		onRegisterEditor(handle);

		return () => {
			onRegisterEditor(null);
		};
	}, [handleDiscardChanges, handleSaveChanges, onRegisterEditor]);

	const editorBody = (
		<Stack gap={6} flex="1">
			{/* Metadata Section */}
			<MetadataEditor
				name={editorState.draft.name}
				description={editorState.draft.description}
				onNameChange={(name) => handleDraftChange("name", name)}
				onDescriptionChange={(desc) =>
					handleDraftChange("description", desc)
				}
			/>

			{/* Main Editor Area */}
			<HStack align="stretch" gap={6} h="600px">
				{/* Left Sidebar: Version History */}
				{showVersionSidebar && (
					<Box
						flex="0 0 250px"
						borderWidth="1px"
						borderColor="whiteAlpha.200"
						borderRadius="md"
						p={4}
						overflowY="auto"
					>
						<VersionHistory
							versions={versionsState.data?.items || []}
							selectedVersionId={editorState.selectedVersionId}
							latestVersionId={latestVersion?.id}
							onSelectVersion={handleSelectVersion}
						/>
					</Box>
				)}

				{/* Right Main Area: Template Editor */}
				<Box flex="1" display="flex" flexDirection="column" gap={4}>
					<TemplateEditor
						model={editorState.draft.model}
						template={editorState.draft.template}
						onModelChange={(model) => handleDraftChange("model", model)}
						onTemplateChange={(template) =>
							handleDraftChange("template", template)
						}
						isViewOnly={editorState.selectedVersionId !== null}
						versions={versionsState.data?.items || []}
						selectedVersionId={editorState.selectedVersionId}
						latestVersionId={latestVersion?.id}
						onSelectVersion={handleSelectVersion}
					/>

					{/* Action Buttons */}
					<HStack gap={2} justify="flex-end">
						{editorState.isDirty && (
							<Button
								size="sm"
								variant="ghost"
								onClick={handleDiscardChanges}
								disabled={editorState.isSaving}
							>
								Discard
							</Button>
						)}
						<Button
							size="sm"
							colorScheme="blue"
							onClick={handleSaveChanges}
							disabled={!editorState.isDirty || editorState.isSaving}
							loading={editorState.isSaving}
						>
							{editorState.isDirty ? "Save Changes" : "No Changes"}
						</Button>
					</HStack>
				</Box>
			</HStack>

			{/* Unsaved indicator */}
			{editorState.isDirty && (
				<Box
					p={3}
					borderRadius="md"
					bg="yellow.900"
					borderLeftWidth="4px"
					borderLeftColor="yellow.400"
				>
					<Text fontSize="sm" color="yellow.100">
						You have unsaved changes
					</Text>
				</Box>
			)}
		</Stack>
	);

	if (variant === "embedded") {
		if (!resolvedPromptId) {
			return (
				<VStack gap={4} justify="center" h="100%">
					<Text color="gray.400" fontSize="sm">
						Select a prompt to view details and manage versions
					</Text>
				</VStack>
			);
		}

		return (
			<Box flex="1" display="flex" flexDirection="column" gap={6}>
				{isLoading ? (
					<Stack gap={4}>
						<Skeleton height="40px" width="100%" />
						<Skeleton height="60px" width="100%" />
						<Skeleton height="400px" width="100%" />
					</Stack>
				) : hasError ? (
					<Text color="red.400">
						{promptState.error || versionsState.error}
					</Text>
				) : !promptState.data ? (
					<Text color="gray.400">Prompt not found</Text>
				) : (
					editorBody
				)}
			</Box>
		);
	}

	return (
		<Container maxW="7xl" py={6}>
			<UnsavedChangesDialog
				isOpen={isOpen}
				onClose={onClose}
				onDiscard={handleConfirmDiscard}
				onSave={handleConfirmSave}
				isSaving={editorState.isSaving}
			/>

			{/* Header with back button */}
			<HStack mb={6}>
				<Button
					size="sm"
					variant="ghost"
					leftIcon={<ChevronLeft size={16} />}
					onClick={() => handleNavigateAway("/")}
				>
					Back
				</Button>
			</HStack>

			{isLoading ? (
				<Stack gap={4}>
					<Skeleton height="40px" width="100%" />
					<Skeleton height="60px" width="100%" />
					<Skeleton height="400px" width="100%" />
				</Stack>
			) : hasError ? (
				<Text color="red.400">{promptState.error || versionsState.error}</Text>
			) : !promptState.data ? (
				<Text color="gray.400">Prompt not found</Text>
			) : (
				editorBody
			)}
		</Container>
	);
}
