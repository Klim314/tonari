import {
	Alert,
	Badge,
	Box,
	Button,
	Flex,
	HStack,
	Heading,
	Icon,
	Separator,
	Text,
} from "@chakra-ui/react";
import { Pause } from "lucide-react";
import { memo } from "react";
import type { TranslationStreamStatus } from "../../../hooks/useChapterTranslationStream";
import type { TranslationSegmentRow } from "../types";
import { SegmentsList } from "./SegmentsList";

export interface TranslationPanelProps {
	translationStatus: TranslationStreamStatus;
	translationError: string | null;
	translationSegments: TranslationSegmentRow[];
	selectedSegmentId: number | null;
	retranslatingSegmentId: number | null;
	onContextSelect: (segmentId: number) => void;
	onSegmentRetranslate: (segmentId: number) => void;
	onClearSelection: () => void;
	primaryLabel: string;
	primaryIcon: typeof Pause;
	primaryColorScheme: string;
	isPrimaryLoading: boolean;
	onPrimaryAction: () => void | Promise<void>;
	disablePrimary: boolean;
}

export const TranslationPanel = memo(function TranslationPanel({
	translationStatus,
	translationError,
	translationSegments,
	selectedSegmentId,
	retranslatingSegmentId,
	onContextSelect,
	onSegmentRetranslate,
	onClearSelection,
	primaryLabel,
	primaryIcon,
	primaryColorScheme,
	isPrimaryLoading,
	onPrimaryAction,
	disablePrimary,
}: TranslationPanelProps) {
	return (
		<Box
			flex="1"
			w="full"
			borderWidth="1px"
			borderRadius="lg"
			px={6}
			pt={4}
			pb={6}
			onClick={onClearSelection}
		>
			<Flex
				direction={{ base: "column", md: "row" }}
				align={{ base: "flex-start", md: "center" }}
				justify="space-between"
				gap={4}
				mb={4}
				minH="10"
			>
				<HStack gap={2}>
					<Heading size="md">Translation</Heading>
					<Badge
						variant="solid"
						colorPalette={getStatusColorScheme(translationStatus)}
					>
						{formatStatusLabel(translationStatus)}
					</Badge>
				</HStack>

				<HStack gap={3} flexWrap="wrap">
					<Button
						variant="outline"
						colorScheme={primaryColorScheme}
						onClick={onPrimaryAction}
						loading={isPrimaryLoading}
						disabled={disablePrimary}
					>
						<HStack gap={2} align="center">
							<Text>{primaryLabel}</Text>
						</HStack>
						<Icon as={primaryIcon} boxSize={4} />
					</Button>
				</HStack>
			</Flex>
			{translationError ? (
				<Alert.Root status="error" borderRadius="md" mb={4}>
					<Alert.Indicator />
					<Alert.Content>
						<Alert.Description>{translationError}</Alert.Description>
					</Alert.Content>
				</Alert.Root>
			) : null}

			<Separator mb={4} />
			{translationSegments.length === 0 ? (
				<Text color="gray.400">
					Start streaming to generate LangChain-powered translations aligned
					with each newline-delimited source segment.
				</Text>
			) : (
				<SegmentsList
					segments={translationSegments}
					selectedSegmentId={selectedSegmentId}
					retranslatingSegmentId={retranslatingSegmentId}
					onContextSelect={onContextSelect}
					onSegmentRetranslate={onSegmentRetranslate}
				/>
			)}
		</Box>
	);
});

function formatStatusLabel(status: TranslationStreamStatus) {
	switch (status) {
		case "connecting":
			return "Connecting";
		case "running":
			return "Streaming";
		case "completed":
			return "Completed";
		case "error":
			return "Error";
		default:
			return "Idle";
	}
}

function getStatusColorScheme(status: TranslationStreamStatus) {
	switch (status) {
		case "connecting":
			return "yellow";
		case "running":
			return "teal";
		case "completed":
			return "green";
		case "error":
			return "red";
		default:
			return "gray";
	}
}
