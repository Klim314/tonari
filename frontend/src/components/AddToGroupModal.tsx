import {
	AlertContent,
	AlertDescription,
	AlertIndicator,
	AlertRoot,
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
	Icon,
	Spinner,
	Stack,
	Text,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Folder } from "lucide-react";
import { useEffect, useState } from "react";
import {
	addChaptersToGroupWorksWorkIdChapterGroupsGroupIdMembersPostMutation,
	listChapterGroupsWorksWorkIdChapterGroupsGetOptions,
} from "../client/@tanstack/react-query.gen";
import { getApiErrorMessage } from "../lib/api";
import { invalidateWorkChapters } from "../lib/queryInvalidation";

interface ChapterGroup {
	id: number;
	work_id: number;
	name: string;
	member_count: number;
}

interface AddToGroupModalProps {
	workId: number;
	selectedChapterIds: number[];
	isOpen: boolean;
	onClose: () => void;
	onSuccess: () => void;
}

export function AddToGroupModal({
	workId,
	selectedChapterIds,
	isOpen,
	onClose,
	onSuccess,
}: AddToGroupModalProps) {
	const queryClient = useQueryClient();
	const [submitting, setSubmitting] = useState<number | null>(null);
	const [error, setError] = useState<string | null>(null);
	const groupQuery = useQuery({
		...listChapterGroupsWorksWorkIdChapterGroupsGetOptions({
			path: { work_id: workId },
		}),
		enabled: isOpen,
	});
	const addToGroup = useMutation({
		...addChaptersToGroupWorksWorkIdChapterGroupsGroupIdMembersPostMutation(),
		onSuccess: async () => {
			await invalidateWorkChapters(queryClient, workId);
		},
	});
	const groups = (groupQuery.data ?? []) as ChapterGroup[];
	const loading = groupQuery.isPending || groupQuery.isFetching;
	const groupsError = groupQuery.error
		? getApiErrorMessage(groupQuery.error, "Failed to load groups")
		: null;

	useEffect(() => {
		if (!isOpen) {
			setError(null);
			setSubmitting(null);
		}
	}, [isOpen]);

	const handleAddToGroup = async (groupId: number) => {
		if (selectedChapterIds.length === 0) {
			setError("No chapters selected");
			return;
		}

		setError(null);
		setSubmitting(groupId);

		try {
			await addToGroup.mutateAsync({
				path: {
					work_id: workId,
					group_id: groupId,
				},
				body: {
					chapter_ids: selectedChapterIds,
				},
			});
			onSuccess();
			onClose();
		} catch (err) {
			const message = getApiErrorMessage(
				err,
				"Failed to add chapters to group",
			);
			setError(message);
		} finally {
			setSubmitting(null);
		}
	};

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(details) => {
				if (!details.open) {
					onClose();
				}
			}}
			lazyMount
			unmountOnExit
		>
			<DialogBackdrop />
			<DialogPositioner>
				<DialogContent>
					<DialogCloseTrigger />
					<DialogHeader>
						<DialogTitle>Add to Existing Group</DialogTitle>
					</DialogHeader>
					<DialogBody>
						<Stack gap={4}>
							<Text color="gray.400" fontSize="sm">
								Select a group to add {selectedChapterIds.length}{" "}
								{selectedChapterIds.length === 1 ? "chapter" : "chapters"} to:
							</Text>

							{loading ? (
								<HStack justify="center" py={6}>
									<Spinner size="sm" />
									<Text color="gray.400">Loading groups...</Text>
								</HStack>
							) : groups.length === 0 ? (
								<Box
									borderWidth="1px"
									borderRadius="md"
									p={6}
									textAlign="center"
								>
									<Text color="gray.500">
										No groups exist yet. Create a group first.
									</Text>
								</Box>
							) : (
								<Stack gap={2}>
									{groups.map((group) => (
										<HStack
											key={group.id}
											borderWidth="1px"
											borderRadius="md"
											p={3}
											justify="space-between"
											transition="background-color 0.2s ease"
											_hover={{ bg: "gray.800" }}
										>
											<HStack gap={3}>
												<Icon as={Folder} boxSize={5} color="teal.400" />
												<Box>
													<Text fontWeight="medium" color="teal.200">
														{group.name}
													</Text>
													<Text fontSize="sm" color="gray.400">
														{group.member_count}{" "}
														{group.member_count === 1 ? "chapter" : "chapters"}
													</Text>
												</Box>
											</HStack>
											<Button
												size="sm"
												colorPalette="teal"
												onClick={() => handleAddToGroup(group.id)}
												loading={submitting === group.id}
												disabled={submitting !== null}
											>
												Add
											</Button>
										</HStack>
									))}
								</Stack>
							)}

							{(error || groupsError) && (
								<AlertRoot status="error">
									<AlertIndicator />
									<AlertContent>
										<AlertDescription>{error ?? groupsError}</AlertDescription>
									</AlertContent>
								</AlertRoot>
							)}
						</Stack>
					</DialogBody>
					<DialogFooter>
						<Button
							variant="ghost"
							onClick={onClose}
							disabled={submitting !== null}
						>
							Cancel
						</Button>
					</DialogFooter>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}
