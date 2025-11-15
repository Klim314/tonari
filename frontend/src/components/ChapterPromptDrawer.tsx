import {
	Alert,
	Badge,
	Box,
	Button,
	Drawer,
	Field,
	HStack,
	Input,
	Stack,
	Text,
	Textarea,
} from "@chakra-ui/react";
import type { ReactElement } from "react";

interface ChapterPromptDrawerProps {
	trigger: ReactElement;
	onClose?: () => void;
	promptName?: string;
	model: string;
	template: string;
	onModelChange: (value: string) => void;
	onTemplateChange: (value: string) => void;
	isDirty: boolean;
	isLoading: boolean;
	isSaving: boolean;
	onReset: () => void;
	onSave: () => void;
	saveDisabledReason?: string | null;
	errorMessage?: string | null;
	secondaryError?: string | null;
	lastSavedAt?: Date | null;
	promptAssigned: boolean;
	workPromptError?: string | null;
}

export function ChapterPromptDrawer({
	trigger,
	onClose,
	promptName,
	model,
	template,
	onModelChange,
	onTemplateChange,
	isDirty,
	isLoading,
	isSaving,
	onReset,
	onSave,
	saveDisabledReason,
	errorMessage,
	secondaryError,
	lastSavedAt,
	promptAssigned,
	workPromptError,
}: ChapterPromptDrawerProps) {
	const handleOpenChange = (details: { open: boolean }) => {
		if (!details.open) {
			onClose?.();
		}
	};

	const disableSave =
		!promptAssigned || !isDirty || Boolean(saveDisabledReason);

	return (
		<Drawer.Root onOpenChange={handleOpenChange} size="lg" placement="right">
			<Drawer.Trigger asChild>{trigger}</Drawer.Trigger>
			<Drawer.Backdrop />
			<Drawer.Positioner>
				<Drawer.Content>
					<Drawer.CloseTrigger />
					<Drawer.Header borderBottomWidth="1px">
						<Text fontWeight="semibold">Chapter Prompt</Text>
						<Text color="gray.500" fontSize="sm">
							{promptName
								? `Editing prompt "${promptName}"`
								: "No prompt assigned to this work"}
						</Text>
					</Drawer.Header>
					<Drawer.Body p={6}>
						<Stack gap={4}>
							{isLoading ? (
								<Text color="gray.500" fontSize="sm">
									Loading prompt details...
								</Text>
							) : null}

							{workPromptError ? (
								<Alert.Root status="error" borderRadius="md">
									<Alert.Indicator />
									<Alert.Content>
										<Alert.Description>{workPromptError}</Alert.Description>
									</Alert.Content>
								</Alert.Root>
							) : null}

							{!promptAssigned ? (
								<Alert.Root status="info" borderRadius="md">
									<Alert.Indicator />
									<Alert.Content>
										<Alert.Title>Assign a prompt first</Alert.Title>
										<Alert.Description>
											Select a prompt for this work from the Work detail page to
											save changes. You can still tweak the prompt below to test
											it before saving.
										</Alert.Description>
									</Alert.Content>
								</Alert.Root>
							) : null}

							{lastSavedAt ? (
								<Text fontSize="sm" color="gray.500">
									Last saved: {lastSavedAt.toLocaleString()}
								</Text>
							) : null}

							<Field.Root>
								<Field.Label>Model</Field.Label>
								<Input
									value={model}
									onChange={(event) => onModelChange(event.target.value)}
									disabled={isLoading}
								/>
							</Field.Root>

							<Field.Root flex="1" display="flex" flexDirection="column">
								<Field.Label>Prompt Template</Field.Label>
								<Textarea
									value={template}
									onChange={(event) => onTemplateChange(event.target.value)}
									fontFamily="mono"
									minH="240px"
									resize="vertical"
									disabled={isLoading}
								/>
							</Field.Root>

							{errorMessage ? (
								<Alert.Root status="error" borderRadius="md">
									<Alert.Indicator />
									<Alert.Content>
										<Alert.Description>{errorMessage}</Alert.Description>
									</Alert.Content>
								</Alert.Root>
							) : null}

							{secondaryError ? (
								<Alert.Root status="error" borderRadius="md">
									<Alert.Indicator />
									<Alert.Content>
										<Alert.Description>{secondaryError}</Alert.Description>
									</Alert.Content>
								</Alert.Root>
							) : null}

							{isDirty ? (
								<Badge colorPalette="yellow" width="fit-content">
									Unsaved changes
								</Badge>
							) : (
								<Text color="gray.500" fontSize="sm">
									No local changes
								</Text>
							)}
						</Stack>
					</Drawer.Body>
					<Drawer.Footer borderTopWidth="1px">
						<HStack gap={3}>
							<Button variant="ghost" onClick={onReset} disabled={!isDirty}>
								Reset
							</Button>
							<Button
								colorScheme="teal"
								onClick={onSave}
								disabled={disableSave}
								title={saveDisabledReason ?? undefined}
								loading={isSaving}
							>
								Save &amp; Update Work Prompt
							</Button>
						</HStack>
						{saveDisabledReason ? (
							<Box mt={3}>
								<Text fontSize="xs" color="gray.500">
									{saveDisabledReason}
								</Text>
							</Box>
						) : null}
					</Drawer.Footer>
				</Drawer.Content>
			</Drawer.Positioner>
		</Drawer.Root>
	);
}
