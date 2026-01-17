import {
	AlertContent,
	AlertDescription,
	AlertIndicator,
	AlertRoot,
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
	FieldErrorText,
	FieldLabel,
	FieldRoot,
	Input,
	Stack,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { getApiErrorMessage } from "../lib/api";

interface CreateChapterGroupModalProps {
	workId: number;
	selectedChapterIds: number[];
	isOpen: boolean;
	onClose: () => void;
	onSuccess: () => void;
}

export function CreateChapterGroupModal({
	workId,
	selectedChapterIds,
	isOpen,
	onClose,
	onSuccess,
}: CreateChapterGroupModalProps) {
	const [groupName, setGroupName] = useState("");
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [validationError, setValidationError] = useState<string | null>(null);

	// Reset form when modal opens/closes
	useEffect(() => {
		if (!isOpen) {
			setGroupName("");
			setSubmitting(false);
			setError(null);
			setValidationError(null);
		}
	}, [isOpen]);

	// Validate group name
	useEffect(() => {
		if (groupName.trim().length === 0 && groupName.length > 0) {
			setValidationError("Group name cannot be empty or whitespace only");
		} else if (groupName.length > 512) {
			setValidationError("Group name must be 512 characters or less");
		} else {
			setValidationError(null);
		}
	}, [groupName]);

	const handleSubmit = async () => {
		const trimmedName = groupName.trim();

		if (!trimmedName) {
			setValidationError("Please enter a group name");
			return;
		}

		if (selectedChapterIds.length === 0) {
			setError("No chapters selected");
			return;
		}

		setError(null);
		setValidationError(null);
		setSubmitting(true);

		try {
			// Using fetch directly since the API client might not be regenerated yet
			const response = await fetch(`/api/works/${workId}/chapter-groups`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					name: trimmedName,
					chapter_ids: selectedChapterIds,
				}),
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || "Failed to create group");
			}

			// Success!
			onSuccess();
			onClose();
		} catch (err) {
			const message = getApiErrorMessage(err, "Failed to create chapter group");
			setError(message);
		} finally {
			setSubmitting(false);
		}
	};

	const canSubmit =
		groupName.trim().length > 0 &&
		!validationError &&
		selectedChapterIds.length > 0 &&
		!submitting;

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
						<DialogTitle>Create Chapter Group</DialogTitle>
					</DialogHeader>
					<DialogBody>
						<Stack gap={4}>
							<FieldRoot required invalid={!!validationError}>
								<FieldLabel htmlFor="group-name-input">Group Name</FieldLabel>
								<Input
									id="group-name-input"
									placeholder="e.g., Arc 1, Volume 1, Prologue"
									value={groupName}
									onChange={(e) => setGroupName(e.target.value)}
									disabled={submitting}
									autoFocus
									onKeyDown={(e) => {
										if (e.key === "Enter" && canSubmit) {
											handleSubmit();
										}
									}}
								/>
								{validationError && (
									<FieldErrorText>{validationError}</FieldErrorText>
								)}
							</FieldRoot>

							{error && (
								<AlertRoot status="error">
									<AlertIndicator />
									<AlertContent>
										<AlertDescription>{error}</AlertDescription>
									</AlertContent>
								</AlertRoot>
							)}
						</Stack>
					</DialogBody>
					<DialogFooter>
						<Button
							variant="ghost"
							mr={3}
							onClick={onClose}
							disabled={submitting}
						>
							Cancel
						</Button>
						<Button
							colorPalette="teal"
							onClick={handleSubmit}
							loading={submitting}
							disabled={!canSubmit}
						>
							Create Group ({selectedChapterIds.length} chapters)
						</Button>
					</DialogFooter>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}
