import { Box, Button, HStack, Input, Stack, Text } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { Prompts } from "../client";
import type { PromptOut } from "../client";
import { useWorkPrompts } from "../hooks/useWorkPrompts";
import { getApiErrorMessage } from "../lib/api";

interface WorkPromptSelectorProps {
	workId: number;
	onPromptSelect?: (prompt: PromptOut) => void;
}

export function WorkPromptSelector({
	workId,
	onPromptSelect,
}: WorkPromptSelectorProps) {
	const [searchQuery, setSearchQuery] = useState("");
	const [isOpen, setIsOpen] = useState(false);
	const [currentPrompt, setCurrentPrompt] = useState<PromptOut | null>(null);
	const [currentPromptLoading, setCurrentPromptLoading] = useState(true);
	const [currentPromptError, setCurrentPromptError] = useState<string | null>(
		null,
	);
	const [isUpdating, setIsUpdating] = useState(false);

	const {
		data: promptsList,
		loading: searchLoading,
		error: searchError,
	} = useWorkPrompts(workId, searchQuery);

	// Load current prompt on mount
	useEffect(() => {
		async function loadCurrentPrompt() {
			try {
				setCurrentPromptLoading(true);
				const response = await Prompts.getWorkPromptPromptsWorksWorkIdPromptGet(
					{
						path: { work_id: workId },
						throwOnError: true,
					},
				);
				setCurrentPrompt(response.data);
				setCurrentPromptError(null);
			} catch (error) {
				const message = getApiErrorMessage(
					error,
					"Failed to load current prompt",
				);
				setCurrentPromptError(message);
			} finally {
				setCurrentPromptLoading(false);
			}
		}

		loadCurrentPrompt();
	}, [workId]);

	async function handleSelectPrompt(prompt: PromptOut) {
		setIsUpdating(true);
		try {
			const response =
				await Prompts.updateWorkPromptPromptsWorksWorkIdPromptPatch({
					path: { work_id: workId },
					body: { prompt_id: prompt.id },
					throwOnError: true,
				});
			setCurrentPrompt(response.data);
			setSearchQuery("");
			setIsOpen(false);
			onPromptSelect?.(response.data);
		} catch (error) {
			const message = getApiErrorMessage(error, "Failed to update prompt");
			setCurrentPromptError(message);
		} finally {
			setIsUpdating(false);
		}
	}

	const displayPrompts = promptsList?.items ?? [];
	const isLoading = searchLoading || currentPromptLoading || isUpdating;

	return (
		<Stack gap={3}>
			<Box position="relative" width="100%">
				{/* Trigger Button */}
				<Button
					onClick={() => setIsOpen(!isOpen)}
					width="100%"
					justifyContent="space-between"
					disabled={isLoading}
					variant="outline"
					fontWeight="normal"
					textAlign="left"
				>
					{isLoading ? (
						<Text fontSize="sm" color="gray.500">
							Loading...
						</Text>
					) : currentPrompt ? (
						<HStack gap={1} width="100%" justify="space-between">
							<Text truncate fontSize="sm">
								{currentPrompt.name}
							</Text>
							<Text fontSize="xs" color="gray.500" ml="auto">
								▼
							</Text>
						</HStack>
					) : (
						<HStack gap={1} width="100%" justify="space-between">
							<Text fontSize="sm" color="gray.500">
								No prompt selected
							</Text>
							<Text fontSize="xs" color="gray.500" ml="auto">
								▼
							</Text>
						</HStack>
					)}
				</Button>

				{/* Dropdown Menu */}
				{isOpen && (
					<Box
						position="absolute"
						top="100%"
						left={0}
						right={0}
						marginTop={1}
						bg="white"
						borderWidth="1px"
						borderRadius="md"
						boxShadow="lg"
						zIndex={10}
					>
						{/* Search Input */}
						<Box p={2} borderBottomWidth="1px">
							<Input
								autoFocus
								placeholder="Search prompts..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								size="sm"
								variant="subtle"
							/>
						</Box>

						{/* Results */}
						<Box maxH="300px" overflowY="auto">
							{searchLoading ? (
								<Box p={3}>
									<Text fontSize="sm" color="gray.500">
										Searching...
									</Text>
								</Box>
							) : searchError ? (
								<Box p={3}>
									<Text fontSize="sm" color="red.500">
										{searchError}
									</Text>
								</Box>
							) : displayPrompts.length === 0 ? (
								<Box p={3}>
									<Text fontSize="sm" color="gray.500">
										No prompts found
									</Text>
								</Box>
							) : (
								displayPrompts.map((prompt) => (
									<Box
										key={prompt.id}
										p={2}
										cursor="pointer"
										_hover={{ bg: "gray.100" }}
										borderBottomWidth="1px"
										_last={{ borderBottomWidth: 0 }}
										onClick={() => handleSelectPrompt(prompt)}
									>
										<HStack justify="space-between" gap={2}>
											<HStack gap={1} flex={1}>
												{currentPrompt?.id === prompt.id && (
													<Text fontSize="sm" fontWeight="bold">
														✓
													</Text>
												)}
												<Text fontSize="sm" truncate>
													{prompt.name}
												</Text>
											</HStack>
										</HStack>
									</Box>
								))
							)}
						</Box>
					</Box>
				)}
			</Box>

			{/* Error Message */}
			{currentPromptError && !isUpdating && (
				<Text fontSize="xs" color="red.500">
					{currentPromptError}
				</Text>
			)}
		</Stack>
	);
}
