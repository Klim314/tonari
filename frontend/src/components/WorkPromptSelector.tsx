import {
	Box,
	Button,
	HStack,
	Input,
	Popover,
	Portal,
	Stack,
	Text,
} from "@chakra-ui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { PromptOut } from "../client";
import {
	getWorkPromptPromptsWorksWorkIdPromptGetQueryKey,
	updateWorkPromptPromptsWorksWorkIdPromptPatchMutation,
} from "../client/@tanstack/react-query.gen";
import { useWorkPromptDetail } from "../hooks/useWorkPromptDetail";
import { useWorkPrompts } from "../hooks/useWorkPrompts";
import { getApiErrorMessage } from "../lib/api";
import {
	invalidateWorkPromptDetail,
	invalidateWorkPromptLists,
} from "../lib/queryInvalidation";
import { NewPromptDialog } from "./NewPromptDialog";

interface WorkPromptSelectorProps {
	workId: number;
	onPromptSelect?: (prompt: PromptOut) => void;
}

export function WorkPromptSelector({
	workId,
	onPromptSelect,
}: WorkPromptSelectorProps) {
	const queryClient = useQueryClient();
	const [searchQuery, setSearchQuery] = useState("");
	const [isOpen, setIsOpen] = useState(false);
	const [isNewDialogOpen, setIsNewDialogOpen] = useState(false);
	const [currentPromptError, setCurrentPromptError] = useState<string | null>(
		null,
	);
	const updatePrompt = useMutation({
		...updateWorkPromptPromptsWorksWorkIdPromptPatchMutation(),
	});

	const {
		data: promptsList,
		loading: searchLoading,
		error: searchError,
	} = useWorkPrompts(workId, searchQuery);
	const {
		data: currentPrompt,
		loading: currentPromptLoading,
		error: workPromptError,
	} = useWorkPromptDetail(workId);

	async function handleSelectPrompt(prompt: PromptOut) {
		try {
			const response = await updatePrompt.mutateAsync({
				path: { work_id: workId },
				body: { prompt_id: prompt.id },
			});
			queryClient.setQueryData(
				getWorkPromptPromptsWorksWorkIdPromptGetQueryKey({
					path: { work_id: workId },
				}),
				response,
			);
			await Promise.all([
				invalidateWorkPromptDetail(queryClient, workId),
				invalidateWorkPromptLists(queryClient, workId),
			]);
			setSearchQuery("");
			setIsOpen(false);
			setCurrentPromptError(null);
			onPromptSelect?.(response);
		} catch (error) {
			const message = getApiErrorMessage(error, "Failed to update prompt");
			setCurrentPromptError(message);
		}
	}

	const displayPrompts = promptsList?.items ?? [];
	const isUpdating = updatePrompt.isPending;
	const isLoading = searchLoading || currentPromptLoading || isUpdating;
	const displayCurrentPromptError = currentPromptError ?? workPromptError;

	return (
		<Stack gap={3}>
			<Popover.Root
				open={isOpen}
				onOpenChange={(e) => setIsOpen(e.open)}
				positioning={{ sameWidth: true }}
			>
				<Popover.Trigger asChild>
					<Button
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
				</Popover.Trigger>
				<Portal>
					<Popover.Positioner>
						<Popover.Content>
							<Popover.Body p={0}>
								<Box p={2} borderBottomWidth="1px">
									<HStack gap={2}>
										<Input
											autoFocus
											placeholder="Search prompts..."
											value={searchQuery}
											onChange={(e) => setSearchQuery(e.target.value)}
											size="sm"
											variant="subtle"
										/>
										<Button
											size="sm"
											variant="outline"
											onClick={() => {
												setIsOpen(false);
												setIsNewDialogOpen(true);
											}}
										>
											+ New
										</Button>
									</HStack>
								</Box>

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
							</Popover.Body>
						</Popover.Content>
					</Popover.Positioner>
				</Portal>
			</Popover.Root>

			{displayCurrentPromptError && !isUpdating && (
				<Text fontSize="xs" color="red.500">
					{displayCurrentPromptError}
				</Text>
			)}

			<NewPromptDialog
				isOpen={isNewDialogOpen}
				onClose={() => setIsNewDialogOpen(false)}
				workId={workId}
				onCreated={(prompt) => {
					onPromptSelect?.(prompt);
				}}
			/>
		</Stack>
	);
}
