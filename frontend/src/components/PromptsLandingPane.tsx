import React, { useCallback, useState } from "react";
import {
	Box,
	Button,
	Container,
	Heading,
	Input,
	Stack,
	Text,
	Skeleton,
	HStack,
	VStack,
	useDisclosure,
} from "@chakra-ui/react";
import { usePrompts } from "../hooks/usePrompts";
import { usePrompt } from "../hooks/usePrompt";
import { usePromptVersions } from "../hooks/usePromptVersions";
import { Prompts } from "../client";
import { MetadataEditor } from "./PromptEditor/MetadataEditor";
import { TemplateEditor } from "./PromptEditor/TemplateEditor";
import { UnsavedChangesDialog } from "./PromptEditor/UnsavedChangesDialog";

interface EditorDraft {
	name: string;
	description: string;
	model: string;
	template: string;
}

interface EditorState {
	draft: EditorDraft;
	isDirty: boolean;
	isSaving: boolean;
	lastSaveTime: Date | null;
	selectedVersionId: number | null;
}

export function PromptsLandingPane() {
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
	const [refreshToken, setRefreshToken] = useState(0);
	const { open: isOpen, onOpen, onClose } = useDisclosure();

	const promptsState = usePrompts(searchQuery, refreshToken);
	const promptState = usePrompt(selectedPromptId, refreshToken);
	const versionsState = usePromptVersions(selectedPromptId, refreshToken);

	const [editorState, setEditorState] = useState<EditorState>({
		draft: {
			name: "",
			description: "",
			model: "",
			template: "",
		},
		isDirty: false,
		isSaving: false,
		lastSaveTime: null,
		selectedVersionId: null,
	});

	// Initialize draft when prompt loads
	const initializeDraft = useCallback(() => {
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

	const handleSelectPrompt = useCallback(
		(promptId: number) => {
			if (editorState.isDirty) {
				onOpen();
				return;
			}
			setSelectedPromptId(promptId);
			setEditorState((prev) => ({
				...prev,
				isDirty: false,
				selectedVersionId: null,
			}));
		},
		[editorState.isDirty, onOpen]
	);

	const handleCreateNewPrompt = async () => {
		try {
			const response = await Prompts.createPromptPromptsPost({
				body: {
					name: "Untitled Prompt",
					description: null,
				},
				throwOnError: true,
			});

			const promptId = response.data.id;
			setSelectedPromptId(promptId);
			setRefreshToken((prev) => prev + 1);
		} catch (error) {
			console.error("Failed to create prompt:", error);
		}
	};

	const metadataSaveTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

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
		[]
	);

	// Auto-save metadata (name and description) independently
	const handleMetadataAutoSave = useCallback(
		(field: "name" | "description", value: string) => {
			handleDraftChange(field, value);

			// Clear existing timeout
			if (metadataSaveTimeoutRef.current) {
				clearTimeout(metadataSaveTimeoutRef.current);
			}

			// Debounce metadata save
			metadataSaveTimeoutRef.current = setTimeout(async () => {
				if (!selectedPromptId) return;
				try {
					await Prompts.updatePromptPromptsPromptIdPatch({
						path: { prompt_id: selectedPromptId },
						body: {
							[field]: value || null,
						},
						throwOnError: true,
					});
				} catch (error) {
					console.error(`Failed to save ${field}:`, error);
				}
			}, 1500);
		},
		[selectedPromptId, handleDraftChange]
	);

	const handleSelectVersion = useCallback((versionId: number) => {
		setEditorState((prev) => ({
			...prev,
			selectedVersionId: versionId,
		}));
	}, []);

	const handleSaveChanges = async () => {
		if (!selectedPromptId || editorState.isSaving) return;

		setEditorState((prev) => ({
			...prev,
			isSaving: true,
		}));

		try {
			// First, update metadata (name, description)
			await Prompts.updatePromptPromptsPromptIdPatch({
				path: { prompt_id: selectedPromptId },
				body: {
					name: editorState.draft.name,
					description: editorState.draft.description || null,
				},
				throwOnError: true,
			});

			// Then, create new version
			await Prompts.appendPromptVersionPromptsPromptIdVersionsPost({
				path: { prompt_id: selectedPromptId },
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
		} catch (error) {
			console.error("Failed to save changes:", error);
			setEditorState((prev) => ({
				...prev,
				isSaving: false,
			}));
		}
	};

	const handleDiscardChanges = () => {
		initializeDraft();
		setEditorState((prev) => ({
			...prev,
			isDirty: false,
			selectedVersionId: null,
		}));
	};

	// Initialize draft when prompt data loads
	if (promptState.data && !editorState.draft.name) {
		initializeDraft();
	}

	const isLoading = promptState.loading || versionsState.loading;
	const hasError = promptState.error || versionsState.error;
	const latestVersion = promptState.data?.latest_version;

	// For viewing selected version (not editing)
	// const selectedVersion = editorState.selectedVersionId
	// 	? versionsState.data?.items.find((v) => v.id === editorState.selectedVersionId)
	// 	: latestVersion;

	return (
		<>
			<UnsavedChangesDialog
				isOpen={isOpen}
				onClose={onClose}
				onDiscard={() => {
					onClose();
					// Will select new prompt after state update
				}}
				onSave={async () => {
					await handleSaveChanges();
					onClose();
				}}
				isSaving={editorState.isSaving}
			/>

			<Container maxW="7xl">
				<Stack direction={{ base: "column", lg: "row" }} gap={6} minH="700px">
					{/* Left: Prompts List */}
					<Box
						flex="0 0 280px"
						borderWidth="1px"
						borderColor="whiteAlpha.200"
						borderRadius="md"
						p={6}
						minH="600px"
						overflowY="auto"
					>
						<Stack gap={4}>
							<Stack gap={2}>
								<HStack justify="space-between" align="center">
									<Heading size="sm">Prompts</Heading>
									<Button size="xs" colorScheme="blue" onClick={handleCreateNewPrompt}>
										+ New
									</Button>
								</HStack>
								<Input
									placeholder="Search prompts..."
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									size="sm"
								/>
							</Stack>

							<Box overflowY="auto" flex="1">
								{promptsState.loading ? (
									<Stack gap={2}>
										{[1, 2, 3].map((i) => (
											<Skeleton key={i} height="60px" width="100%" />
										))}
									</Stack>
								) : promptsState.error ? (
									<Text color="red.400" fontSize="sm">
										{promptsState.error}
									</Text>
								) : !promptsState.data?.items ||
									promptsState.data.items.length === 0 ? (
									<Text color="gray.400" fontSize="sm">
										No prompts found
									</Text>
								) : (
									<Stack gap={2}>
										{promptsState.data.items.map((prompt) => (
											<Box
												key={prompt.id}
												p={3}
												borderWidth="1px"
												borderColor={
													selectedPromptId === prompt.id
														? "blue.500"
														: "whiteAlpha.100"
												}
												borderRadius="md"
												bg={
													selectedPromptId === prompt.id
														? "whiteAlpha.50"
														: "transparent"
												}
												cursor="pointer"
												_hover={{ borderColor: "blue.400" }}
												onClick={() => handleSelectPrompt(prompt.id)}
											>
												<Text fontWeight="500" fontSize="sm">
													{prompt.name}
												</Text>
												{prompt.description && (
													<Text
														color="gray.400"
														fontSize="xs"
														mt={1}
														lineClamp={2}
													>
														{prompt.description}
													</Text>
												)}
											</Box>
										))}
									</Stack>
								)}
							</Box>
						</Stack>
					</Box>

					{/* Right: Editor */}
					<Box flex="1" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="md" p={6} minH="600px" display="flex" flexDirection="column" gap={4}>
						{!selectedPromptId ? (
							<VStack gap={4} justify="center" h="100%">
								<Text color="gray.400" fontSize="sm">
									Select a prompt to view details and manage versions
								</Text>
							</VStack>
						) : isLoading ? (
							<Stack gap={4}>
								<Skeleton height="40px" width="100%" />
								<Skeleton height="20px" width="80%" />
								<Skeleton height="300px" width="100%" />
							</Stack>
						) : hasError ? (
							<Text color="red.400">{hasError}</Text>
						) : promptState.data ? (
							<VStack align="stretch" gap={4} flex="1" overflow="hidden">
								{/* Metadata */}
								<MetadataEditor
									name={editorState.draft.name}
									description={editorState.draft.description}
									onNameChange={(name) => handleMetadataAutoSave("name", name)}
									onDescriptionChange={(desc) => handleMetadataAutoSave("description", desc)}
								/>

								{/* Template Editor with inline version selector */}
								<Box flex="1" display="flex" flexDirection="column" gap={3} overflow="hidden">
									<TemplateEditor
										model={editorState.draft.model}
										template={editorState.draft.template}
										onModelChange={(model) => handleDraftChange("model", model)}
										onTemplateChange={(template) => handleDraftChange("template", template)}
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
							</VStack>
						) : null}
					</Box>
				</Stack>
			</Container>
		</>
	);
}
