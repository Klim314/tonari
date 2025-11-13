import { useState } from "react";
import {
	Box,
	Button,
	Container,
	Heading,
	Input,
	Stack,
	Text,
	Skeleton,
	Badge,
	Textarea,
	FieldLabel,
	FieldRoot,
	MenuRoot,
	MenuTrigger,
	MenuContent,
	MenuItem,
} from "@chakra-ui/react";
import { SquarePen } from "lucide-react";
import { usePrompts } from "../hooks/usePrompts";
import { usePrompt } from "../hooks/usePrompt";
import { usePromptVersions } from "../hooks/usePromptVersions";
import { Prompts } from "../client";

export function PromptsLandingPane() {
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
	const [refreshToken, setRefreshToken] = useState(0);
	const [newVersionModel, setNewVersionModel] = useState("");
	const [newVersionTemplate, setNewVersionTemplate] = useState("");
	const [isSubmittingVersion, setIsSubmittingVersion] = useState(false);

	// Edit mode for metadata
	const [isEditingMetadata, setIsEditingMetadata] = useState(false);
	const [editingName, setEditingName] = useState("");
	const [editingDescription, setEditingDescription] = useState("");
	const [isSubmittingMetadata, setIsSubmittingMetadata] = useState(false);

	// Version selector
	const [selectedVersionId, setSelectedVersionId] = useState<number | null>(
		null,
	);

	// Create version inline form
	const [isCreatingVersion, setIsCreatingVersion] = useState(false);

	const promptsState = usePrompts(searchQuery, refreshToken);
	const promptState = usePrompt(selectedPromptId, refreshToken);
	const versionsState = usePromptVersions(selectedPromptId, refreshToken);

	const handleSelectPrompt = (promptId: number) => {
		setSelectedPromptId(promptId);
		setIsEditingMetadata(false);
		setSelectedVersionId(null);
	};

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
			setEditingName("Untitled Prompt");
			setEditingDescription("");
			setIsEditingMetadata(true);
			setIsCreatingVersion(true);
			setRefreshToken((prev) => prev + 1);
		} catch (error) {
			console.error("Failed to create prompt:", error);
		}
	};

	const handleStartEditMetadata = () => {
		if (promptState.data) {
			setEditingName(promptState.data.name);
			setEditingDescription(promptState.data.description || "");
			setIsEditingMetadata(true);
		}
	};

	const handleSaveMetadata = async () => {
		if (!selectedPromptId || !editingName.trim()) {
			return;
		}

		setIsSubmittingMetadata(true);
		try {
			await Prompts.updatePromptPromptsPromptIdPatch({
				path: { prompt_id: selectedPromptId },
				body: {
					name: editingName,
					description: editingDescription || null,
				},
				throwOnError: true,
			});

			setIsEditingMetadata(false);
			setRefreshToken((prev) => prev + 1);
		} catch (error) {
			console.error("Failed to save metadata:", error);
		} finally {
			setIsSubmittingMetadata(false);
		}
	};

	const handleCancelEditMetadata = () => {
		setIsEditingMetadata(false);
	};

	const handleAddVersion = async () => {
		if (!selectedPromptId || !newVersionModel || !newVersionTemplate) {
			return;
		}

		setIsSubmittingVersion(true);
		try {
			await Prompts.appendPromptVersionPromptsPromptIdVersionsPost({
				path: { prompt_id: selectedPromptId },
				body: {
					model: newVersionModel,
					template: newVersionTemplate,
				},
				throwOnError: true,
			});

			setNewVersionModel("");
			setNewVersionTemplate("");
			setIsCreatingVersion(false);
			setSelectedVersionId(null);
			setRefreshToken((prev) => prev + 1);
		} catch (error) {
			console.error("Failed to add version:", error);
		} finally {
			setIsSubmittingVersion(false);
		}
	};

	const handleToggleCreateVersion = () => {
		setIsCreatingVersion(!isCreatingVersion);
		if (isCreatingVersion) {
			setNewVersionModel("");
			setNewVersionTemplate("");
		}
	};

	const handleCancelCreateVersion = () => {
		setIsCreatingVersion(false);
		setNewVersionModel("");
		setNewVersionTemplate("");
	};

	const handleSelectVersion = (versionId: number) => {
		setSelectedVersionId(versionId);
	};

	return (
		<Container maxW="6xl">
			<Stack direction={{ base: "column", lg: "row" }} gap={6}>
				{/* Filter Rail */}
				<Box
					flex="1"
					borderWidth="1px"
					borderColor="whiteAlpha.200"
					borderRadius="md"
					p={6}
					minH="400px"
				>
					<Stack gap={4}>
						<Stack gap={2}>
							<Stack direction="row" justify="space-between" align="center">
								<Heading size="sm">Prompts</Heading>
								<Button size="xs" colorScheme="blue" onClick={handleCreateNewPrompt}>
									+ New
								</Button>
							</Stack>
							<Input
								placeholder="Search prompts..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								size="sm"
							/>
						</Stack>

						<Box overflowY="auto" maxH="600px">
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

				{/* Detail / Editor Pane */}
				<Box
					flex="2"
					borderWidth="1px"
					borderColor="whiteAlpha.200"
					borderRadius="md"
					p={6}
					minH="400px"
				>
					{!selectedPromptId ? (
						<Stack gap={4} justify="center" h="100%">
							<Text color="gray.400" fontSize="sm">
								Select a prompt to view details and manage versions
							</Text>
						</Stack>
					) : promptState.loading ? (
						<Stack gap={4}>
							<Skeleton height="40px" width="100%" />
							<Skeleton height="20px" width="80%" />
							<Skeleton height="200px" width="100%" />
						</Stack>
					) : promptState.error ? (
						<Text color="red.400">{promptState.error}</Text>
					) : promptState.data ? (
						<Stack gap={4}>
							{/* Prompt Header / Edit Mode */}
							{isEditingMetadata ? (
								<Stack gap={3}>
									<FieldRoot>
										<FieldLabel htmlFor="edit-name-input">Name</FieldLabel>
										<Input
											id="edit-name-input"
											value={editingName}
											onChange={(e) => setEditingName(e.target.value)}
											disabled={isSubmittingMetadata}
											autoFocus
										/>
									</FieldRoot>
									<FieldRoot>
										<FieldLabel htmlFor="edit-description-input">
											Description
										</FieldLabel>
										<Textarea
											id="edit-description-input"
											value={editingDescription}
											onChange={(e) => setEditingDescription(e.target.value)}
											disabled={isSubmittingMetadata}
											minH="80px"
											fontSize="sm"
										/>
									</FieldRoot>
									<Stack direction="row" gap={2}>
										<Button
											size="sm"
											colorScheme="blue"
											onClick={handleSaveMetadata}
											loading={isSubmittingMetadata}
											disabled={!editingName.trim() || isSubmittingMetadata}
										>
											Save
										</Button>
										<Button
											size="sm"
											variant="ghost"
											onClick={handleCancelEditMetadata}
											disabled={isSubmittingMetadata}
										>
											Cancel
										</Button>
									</Stack>
								</Stack>
							) : (
								<Stack gap={2}>
									<Stack
										direction="row"
										justify="space-between"
										align="flex-start"
									>
										<Heading size="lg">{promptState.data.name}</Heading>
										<Button
											size="xs"
											variant="ghost"
											onClick={handleStartEditMetadata}
										>
											<SquarePen size={16} />
											Edit
										</Button>
									</Stack>
									{promptState.data.description && (
										<Text color="gray.400" fontSize="sm">
											{promptState.data.description}
										</Text>
									)}
									{promptState.data.latest_version && (
										<Stack direction="row" gap={2} flexWrap="wrap">
											<Badge colorScheme="blue">
												v{promptState.data.latest_version.version_number}
											</Badge>
											<Badge colorScheme="gray">
												{promptState.data.latest_version.model}
											</Badge>
											{promptState.data.latest_version.created_by && (
												<Text fontSize="xs" color="gray.400">
													by {promptState.data.latest_version.created_by}
												</Text>
											)}
										</Stack>
									)}
								</Stack>
							)}

							<Box height="1px" bg="whiteAlpha.200" />

							{/* Version Selector and Preview */}
							{promptState.data.latest_version ? (
								<Stack gap={2}>
									<Stack direction="row" justify="space-between" align="center">
										<Heading size="sm">Template</Heading>
										{versionsState.data &&
											versionsState.data.items.length > 1 && (
												<MenuRoot>
													<MenuTrigger asChild>
														<Button size="xs" variant="outline">
															v
															{selectedVersionId
																? versionsState.data.items.find(
																		(v) => v.id === selectedVersionId,
																	)?.version_number
																: promptState.data.latest_version
																		.version_number}{" "}
															▼
														</Button>
													</MenuTrigger>
													<MenuContent maxH="300px" overflowY="auto">
														{versionsState.data.items.map((version) => (
															<MenuItem
																key={version.id}
																value={version.id.toString()}
																onClick={() => handleSelectVersion(version.id)}
																fontFamily="body"
																fontSize="sm"
															>
																v{version.version_number} - {version.model}
																{selectedVersionId === version.id && " ✓"}
															</MenuItem>
														))}
													</MenuContent>
												</MenuRoot>
											)}
									</Stack>
									{selectedVersionId &&
									versionsState.data &&
									versionsState.data.items.find(
										(v) => v.id === selectedVersionId,
									) ? (
										<Box
											p={3}
											borderWidth="2px"
											borderColor="blue.400"
											borderRadius="md"
											bg="whiteAlpha.50"
											fontFamily="mono"
											fontSize="xs"
											maxH="200px"
											overflowY="auto"
											whiteSpace="pre-wrap"
											wordBreak="break-word"
										>
											{
												versionsState.data.items.find(
													(v) => v.id === selectedVersionId,
												)?.template
											}
											<Text fontSize="xs" color="blue.300" mt={2}>
												Unsaved preview - click "Create New Version" to save
											</Text>
										</Box>
									) : (
										<Box
											p={3}
											borderWidth="1px"
											borderColor="whiteAlpha.100"
											borderRadius="md"
											bg="whiteAlpha.50"
											fontFamily="mono"
											fontSize="xs"
											maxH="200px"
											overflowY="auto"
											whiteSpace="pre-wrap"
											wordBreak="break-word"
										>
											{promptState.data.latest_version.template}
										</Box>
									)}
								</Stack>
							) : (
								<Stack gap={2}>
									<Heading size="sm">No Versions Yet</Heading>
									<Text color="gray.400" fontSize="sm">
										Create the first version to begin using this prompt
									</Text>
								</Stack>
							)}

							{/* Create New Version Button / Inline Form */}
							{!isCreatingVersion ? (
								<Button
									size="sm"
									colorScheme="blue"
									onClick={handleToggleCreateVersion}
								>
									Create New Version
								</Button>
							) : (
								<Stack
									gap={3}
									p={4}
									borderWidth="1px"
									borderColor="whiteAlpha.100"
									borderRadius="md"
									bg="whiteAlpha.50"
								>
									<FieldRoot>
										<FieldLabel htmlFor="inline-model-input">Model</FieldLabel>
										<Input
											id="inline-model-input"
											placeholder="e.g., gpt-4"
											value={newVersionModel}
											onChange={(e) => setNewVersionModel(e.target.value)}
											disabled={isSubmittingVersion}
											size="sm"
										/>
									</FieldRoot>
									<FieldRoot>
										<FieldLabel htmlFor="inline-template-input">
											Template
										</FieldLabel>
										<Textarea
											id="inline-template-input"
											placeholder="Enter template with {variables}..."
											value={newVersionTemplate}
											onChange={(e) => setNewVersionTemplate(e.target.value)}
											minH="150px"
											fontFamily="mono"
											fontSize="sm"
											disabled={isSubmittingVersion}
										/>
									</FieldRoot>
									<Stack direction="row" gap={2}>
										<Button
											size="sm"
											colorScheme="blue"
											onClick={handleAddVersion}
											loading={isSubmittingVersion}
											disabled={
												!newVersionModel ||
												!newVersionTemplate ||
												isSubmittingVersion
											}
										>
											Create Version
										</Button>
										<Button
											size="sm"
											variant="ghost"
											onClick={handleCancelCreateVersion}
											disabled={isSubmittingVersion}
										>
											Cancel
										</Button>
									</Stack>
								</Stack>
							)}
						</Stack>
					) : null}
				</Box>
			</Stack>
		</Container>
	);
}
