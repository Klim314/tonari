import {
	Badge,
	Box,
	Button,
	Field,
	HStack,
	Heading,
	Text,
	Textarea,
	VStack,
} from "@chakra-ui/react";
import { ModelAutocomplete } from "../PromptEditor/ModelAutocomplete";
// Assuming we have a hook or component for Prompt selection, or we'll build a simple one
// For MVP, maybe just a text input for template?
// The plan said "Prompt Selector (dropdown + Custom option)".
// Let's stick to simple "Custom" for now as per "manual text input" focus,
// but we should probably allow selecting existing prompts if easy.
// I'll simulate a PromptSelector with a simple Input for now to keep it moving,
// or check if there is a reusable PromptSelector.
// There is `WorkPromptSelector.tsx`, but that's for Works.
// `PromptEditor` has logic.
// Let's build a simple lane first.

export interface LabLaneConfig {
	id: string;
	model: string;
	template: string;
	status: "idle" | "running" | "completed" | "error";
	output: string;
	error?: string;
	metrics?: {
		durationMs?: number;
		tokens?: number;
	};
}

interface LabLaneProps {
	config: LabLaneConfig;
	onConfigChange: (id: string, updates: Partial<LabLaneConfig>) => void;
	onRemove: (id: string) => void;
	models: string[];
}

export function LabLane({
	config,
	onConfigChange,
	onRemove,
	models,
}: LabLaneProps) {
	return (
		<Box
			minW="350px"
			w="350px"
			bg="white"
			borderRadius="md"
			borderWidth="1px"
			borderColor="gray.200"
			display="flex"
			flexDirection="column"
			h="100%"
			boxShadow="sm"
		>
			{/* Header / Config */}
			<VStack p={4} gap={3} align="stretch" borderBottomWidth="1px" borderColor="gray.100">
				<HStack justify="space-between">
					<Heading size="sm" color="gray.700">Configuration</Heading>
					<Button size="xs" colorPalette="red" variant="ghost" onClick={() => onRemove(config.id)}>
						Close
					</Button>
				</HStack>

				<Field.Root>
					<Field.Label fontSize="xs" color="gray.600">Model</Field.Label>
					<ModelAutocomplete
						value={config.model}
						onChange={(val) => onConfigChange(config.id, { model: val })}
						placeholder="Select Model..."
						models={models}
					/>
				</Field.Root>

				<Field.Root>
					<Field.Label fontSize="xs" color="gray.600">System Prompt / Template</Field.Label>
					<Textarea
						size="sm"
						fontSize="xs"
						value={config.template}
						onChange={(e) => onConfigChange(config.id, { template: e.target.value })}
						placeholder="Enter system prompt..."
						rows={3}
						bg="white"
						borderColor="gray.200"
					/>
				</Field.Root>
			</VStack>

			{/* Output Area */}
			<Box flex="1" p={4} overflowY="auto" bg="gray.50">
				{config.status === "error" ? (
					<Text color="red.500" fontSize="sm">{config.error}</Text>
				) : (
					<Text
						whiteSpace="pre-wrap"
						fontSize="sm"
						color={config.output ? "gray.800" : "gray.400"}
					>
						{config.output || "Waiting for run..."}
					</Text>
				)}
			</Box>

			{/* Footer / Status */}
			<HStack p={2} bg="white" borderTopWidth="1px" borderColor="gray.100" justify="space-between">
				<Badge
					colorPalette={
						config.status === "running" ? "blue" :
							config.status === "completed" ? "green" :
								config.status === "error" ? "red" : "gray"
					}
					variant="subtle"
					fontSize="xs"
				>
					{config.status.toUpperCase()}
				</Badge>
				{config.metrics?.durationMs && (
					<Text fontSize="xs" color="gray.500">
						{config.metrics.durationMs}ms
					</Text>
				)}
			</HStack>
		</Box>
	);
}
