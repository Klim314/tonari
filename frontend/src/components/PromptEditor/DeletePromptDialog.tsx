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
	Text,
	VStack,
} from "@chakra-ui/react";
import { useCallback } from "react";

interface DeletePromptDialogProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: () => Promise<void>;
	isDeleting: boolean;
	promptName?: string;
	error?: string | null;
}

export function DeletePromptDialog({
	isOpen,
	onClose,
	onConfirm,
	isDeleting,
	promptName,
	error,
}: DeletePromptDialogProps) {
	const handleConfirm = useCallback(async () => {
		await onConfirm();
	}, [onConfirm]);

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(event) => {
				if (!event.open) onClose();
			}}
			trapFocus
			motionPreset="scale"
		>
			<DialogBackdrop bg="blackAlpha.600" />
			<DialogPositioner>
				<DialogContent maxW="sm" w="100%">
					<DialogCloseTrigger />
					<DialogHeader>
						<DialogTitle>Delete Prompt</DialogTitle>
					</DialogHeader>
					<DialogBody>
						<VStack gap={4} align="stretch">
							<Text>
								Are you sure you want to delete
								<Text as="span" fontWeight="semibold">
									{" "}
									{promptName || "this prompt"}
								</Text>
								? This will hide it from editors but keeps previous versions for
								linked works.
							</Text>
							{error && (
								<Box
									p={3}
									borderWidth="1px"
									borderColor="red.500"
									borderRadius="md"
									bg="red.900"
								>
									<Text fontSize="sm" color="red.100">
										{error}
									</Text>
								</Box>
							)}
						</VStack>
					</DialogBody>
					<DialogFooter>
						<Button variant="ghost" onClick={onClose} disabled={isDeleting}>
							Cancel
						</Button>
						<Button
							colorScheme="red"
							onClick={handleConfirm}
							loading={isDeleting}
							disabled={isDeleting}
						>
							Delete
						</Button>
					</DialogFooter>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}
