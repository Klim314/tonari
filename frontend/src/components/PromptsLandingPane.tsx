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
import { Prompts } from "../client";
import { PromptEditor } from "./PromptEditor";
import { UnsavedChangesDialog } from "./PromptEditor/UnsavedChangesDialog";
import { usePromptEditor } from "../hooks/usePromptEditor";

export function PromptsLandingPane() {
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
	const [refreshToken, setRefreshToken] = useState(0);
	const { open: isDialogOpen, onOpen, onClose } = useDisclosure();
	const [pendingPromptId, setPendingPromptId] = useState<number | null>(null);
	const [isEditorDirty, setIsEditorDirty] = useState(false);
	const [isEditorSaving, setIsEditorSaving] = useState(false);
	const { registerEditor, saveChanges, discardChanges } = usePromptEditor();

	const promptsState = usePrompts(searchQuery, refreshToken);

	const handleSelectPrompt = useCallback(
		(promptId: number) => {
			if (promptId === selectedPromptId) {
				return;
			}
			if (isEditorDirty) {
				setPendingPromptId(promptId);
				onOpen();
				return;
			}
			setSelectedPromptId(promptId);
		},
		[isEditorDirty, onOpen, selectedPromptId]
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

	const handleDialogDiscard = useCallback(() => {
		if (pendingPromptId !== null) {
			discardChanges();
			setSelectedPromptId(pendingPromptId);
			setPendingPromptId(null);
		}
		onClose();
	}, [discardChanges, onClose, pendingPromptId]);

	const handleDialogSave = useCallback(async () => {
		await saveChanges();
		if (pendingPromptId !== null) {
			setSelectedPromptId(pendingPromptId);
			setPendingPromptId(null);
		}
		onClose();
	}, [onClose, pendingPromptId, saveChanges]);

	const handlePromptSaved = useCallback(() => {
		setRefreshToken((prev) => prev + 1);
	}, []);

	return (
		<>
			<UnsavedChangesDialog
				isOpen={isDialogOpen}
				onClose={onClose}
				onDiscard={handleDialogDiscard}
				onSave={handleDialogSave}
				isSaving={isEditorSaving}
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
                        ) : (
							<PromptEditor
								variant="embedded"
								promptId={selectedPromptId}
								onDirtyChange={setIsEditorDirty}
								onSavingChange={setIsEditorSaving}
								onPromptSaved={handlePromptSaved}
								showVersionSidebar={false}
								onRegisterEditor={registerEditor}
							/>
                        )}
					</Box>
				</Stack>
			</Container>
		</>
	);
}
