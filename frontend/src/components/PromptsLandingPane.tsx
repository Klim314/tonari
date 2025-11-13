import { useState } from "react";
import {
	Box,
	Button,
	Container,
	Heading,
	HStack,
	Input,
	Stack,
	Text,
	Skeleton,
	Badge,
	Textarea,
	FieldLabel,
	FieldRoot,
	DialogRoot,
	DialogBackdrop,
	DialogPositioner,
	DialogContent,
	DialogCloseTrigger,
	DialogHeader,
	DialogTitle,
	DialogBody,
	DialogFooter,
} from "@chakra-ui/react";
import { usePrompts } from "../hooks/usePrompts";
import { usePrompt } from "../hooks/usePrompt";
import { usePromptVersions } from "../hooks/usePromptVersions";
import { Prompts } from "../client";

export function PromptsLandingPane() {
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
	const [refreshToken, setRefreshToken] = useState(0);
	const [isDialogOpen, setIsDialogOpen] = useState(false);
	const [newVersionModel, setNewVersionModel] = useState("");
	const [newVersionTemplate, setNewVersionTemplate] = useState("");
	const [isSubmittingVersion, setIsSubmittingVersion] = useState(false);

	const promptsState = usePrompts(searchQuery, refreshToken);
	const promptState = usePrompt(selectedPromptId, refreshToken);
	const versionsState = usePromptVersions(selectedPromptId, refreshToken);

	const handleSelectPrompt = (promptId: number) => {
		setSelectedPromptId(promptId);
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
			setIsDialogOpen(false);
			setRefreshToken((prev) => prev + 1);
		} catch (error) {
			console.error("Failed to add version:", error);
		} finally {
			setIsSubmittingVersion(false);
		}
	};

	const handleOpenDialog = () => {
		setIsDialogOpen(true);
	};

	const handleCloseDialog = () => {
		setIsDialogOpen(false);
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
							<Heading size="sm">Prompts</Heading>
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
							) : !promptsState.data?.items || promptsState.data.items.length === 0 ? (
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
													noOfLines={2}
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
							{/* Prompt Header */}
							<Stack gap={2}>
								<Heading size="lg">{promptState.data.name}</Heading>
								{promptState.data.description && (
									<Text color="gray.400" fontSize="sm">
										{promptState.data.description}
									</Text>
								)}
								{promptState.data.latest_version && (
									<HStack gap={2} flexWrap="wrap">
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
									</HStack>
								)}
							</Stack>

							<Box height="1px" bg="whiteAlpha.200" />

							{/* Latest Version Preview */}
							{promptState.data.latest_version && (
								<Stack gap={2}>
									<Heading size="sm">Latest Version Template</Heading>
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
								</Stack>
							)}

							{/* Action Buttons */}
							<HStack gap={2}>
								<Button
									size="sm"
									colorScheme="blue"
									onClick={handleOpenDialog}
								>
									Create New Version
								</Button>
								{versionsState.data && versionsState.data.total > 1 && (
									<Button size="sm" variant="outline">
										View History ({versionsState.data.total})
									</Button>
								)}
							</HStack>

							{/* Versions List */}
							{versionsState.data && versionsState.data.items.length > 1 && (
								<Stack gap={2}>
									<Heading size="sm">Version History</Heading>
									<Stack gap={2} maxH="300px" overflowY="auto">
										{versionsState.data.items.slice(1).map((version) => (
											<Box
												key={version.id}
												p={2}
												borderWidth="1px"
												borderColor="whiteAlpha.100"
												borderRadius="md"
												width="100%"
												fontSize="xs"
											>
												<HStack gap={2}>
													<Badge>v{version.version_number}</Badge>
													<Text color="gray.400">{version.model}</Text>
													{version.created_by && (
														<Text color="gray.500">
															by {version.created_by}
														</Text>
													)}
												</HStack>
											</Box>
										))}
									</Stack>
								</Stack>
							)}
						</Stack>
					) : null}
				</Box>
			</Stack>

			{/* Add Version Dialog */}
			<DialogRoot
				open={isDialogOpen}
				onOpenChange={(details) => setIsDialogOpen(details.open)}
				lazyMount
				unmountOnExit
			>
				<DialogBackdrop />
				<DialogPositioner>
					<DialogContent>
						<DialogCloseTrigger />
						<DialogHeader>
							<DialogTitle>Create New Version</DialogTitle>
						</DialogHeader>
						<DialogBody>
							<Stack gap={4}>
								<FieldRoot>
									<FieldLabel htmlFor="model-input">Model</FieldLabel>
									<Input
										id="model-input"
										placeholder="e.g., gpt-4"
										value={newVersionModel}
										onChange={(e) => setNewVersionModel(e.target.value)}
										size="sm"
									/>
								</FieldRoot>
								<FieldRoot>
									<FieldLabel htmlFor="template-input">Template</FieldLabel>
									<Textarea
										id="template-input"
										placeholder="Enter template with {variables}..."
										value={newVersionTemplate}
										onChange={(e) => setNewVersionTemplate(e.target.value)}
										minH="150px"
										fontFamily="mono"
										fontSize="sm"
									/>
								</FieldRoot>
							</Stack>
						</DialogBody>
						<DialogFooter gap={2}>
							<Button
								variant="ghost"
								onClick={handleCloseDialog}
								isDisabled={isSubmittingVersion}
							>
								Cancel
							</Button>
							<Button
								colorScheme="blue"
								onClick={handleAddVersion}
								isLoading={isSubmittingVersion}
								isDisabled={
									!newVersionModel || !newVersionTemplate || isSubmittingVersion
								}
							>
								Create Version
							</Button>
						</DialogFooter>
					</DialogContent>
				</DialogPositioner>
			</DialogRoot>
		</Container>
	);
}
