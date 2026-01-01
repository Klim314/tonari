import { Box, Stack, Text, Textarea, VStack } from "@chakra-ui/react";
import { FieldLabel, FieldRoot } from "@chakra-ui/react";
import type { PromptVersionOut } from "../../client";
import { useModels } from "../../hooks/useModels";
import { ModelAutocomplete } from "./ModelAutocomplete";
import { VersionSelector } from "./VersionSelector";

interface TemplateEditorProps {
	model: string;
	template: string;
	onModelChange: (model: string) => void;
	onTemplateChange: (template: string) => void;
	isViewOnly?: boolean;
	versions?: PromptVersionOut[];
	selectedVersionId?: number | null;
	latestVersionId?: number;
	onSelectVersion?: (versionId: number) => void;
}

export function TemplateEditor({
	model,
	template,
	onModelChange,
	onTemplateChange,
	isViewOnly = false,
	versions = [],
	selectedVersionId = null,
	latestVersionId,
	onSelectVersion,
}: TemplateEditorProps) {
	const { data: availableModels, loading: loadingModels } = useModels();

	return (
		<VStack align="stretch" gap={4} flex="1" display="flex">
			{/* Header with Model and Version Selector */}
			<Stack
				direction="row"
				gap={4}
				width="100%"
				justify="space-between"
				align="flex-end"
			>
				<FieldRoot flex="1" minW={0}>
					<FieldLabel htmlFor="model-input" mb={2}>
						Model
					</FieldLabel>
					<ModelAutocomplete
						value={model}
						onChange={onModelChange}
						models={availableModels}
						placeholder={loadingModels ? "Loading models..." : "Select or type a model"}
						disabled={isViewOnly}
					/>
				</FieldRoot>

				{versions.length > 0 && onSelectVersion && (
					<Box flexShrink={0} width="fit-content">
						<FieldRoot width="fit-content">
							<FieldLabel fontSize="sm" mb={2}>
								Version
							</FieldLabel>
							<VersionSelector
								versions={versions}
								selectedVersionId={selectedVersionId}
								latestVersionId={latestVersionId}
								onSelectVersion={onSelectVersion}
							/>
						</FieldRoot>
					</Box>
				)}
			</Stack>

			{/* Template Editor */}
			<FieldRoot flex="1" display="flex" flexDirection="column">
				<FieldLabel htmlFor="template-input">Prompt Template</FieldLabel>
				<Textarea
					id="template-input"
					placeholder="Enter your prompt template here. Use {variable_name} for dynamic content."
					value={template}
					onChange={(e) => onTemplateChange(e.target.value)}
					disabled={isViewOnly}
					fontFamily="mono"
					fontSize="sm"
					resize="vertical"
					flex="1"
					minH="300px"
				/>
			</FieldRoot>

			{/* View Mode Indicator */}
			{isViewOnly && (
				<Box
					p={2}
					borderRadius="md"
					bg="blue.900"
					borderLeftWidth="3px"
					borderLeftColor="blue.400"
				>
					<Text fontSize="xs" color="blue.100">
						Viewing historical version. Select a different version or the latest
						to make changes.
					</Text>
				</Box>
			)}
		</VStack>
	);
}
