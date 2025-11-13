import {
	DialogRoot,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogBody,
	DialogFooter,
	DialogCloseTrigger,
} from "@chakra-ui/react";
import { Button, Text, VStack } from "@chakra-ui/react";

interface UnsavedChangesDialogProps {
	isOpen: boolean;
	onClose: () => void;
	onDiscard: () => void;
	onSave: () => Promise<void>;
	isSaving: boolean;
}

export function UnsavedChangesDialog({
	isOpen,
	onClose,
	onDiscard,
	onSave,
	isSaving,
}: UnsavedChangesDialogProps) {
	return (
		<DialogRoot open={isOpen} onOpenChange={(e) => { if (!e.open) onClose(); }}>
			<DialogContent>
				<DialogCloseTrigger />
				<DialogHeader>
					<DialogTitle>Unsaved Changes</DialogTitle>
				</DialogHeader>
				<DialogBody>
					<VStack gap={3} align="stretch">
						<Text>
							You have unsaved changes. Do you want to save them before leaving?
						</Text>
					</VStack>
				</DialogBody>
				<DialogFooter>
					<Button
						variant="ghost"
						onClick={onDiscard}
						disabled={isSaving}
					>
						Discard
					</Button>
					<Button
						colorScheme="blue"
						onClick={onSave}
						loading={isSaving}
						disabled={isSaving}
					>
						Save
					</Button>
				</DialogFooter>
			</DialogContent>
		</DialogRoot>
	);
}
