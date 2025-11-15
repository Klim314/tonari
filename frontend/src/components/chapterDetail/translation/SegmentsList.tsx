import { Box, Menu, Portal, Stack, Text } from "@chakra-ui/react";
import { memo } from "react";
import type { TranslationSegmentRow } from "../types";

interface SegmentsListProps {
	segments: TranslationSegmentRow[];
	selectedSegmentId: number | null;
	retranslatingSegmentId: number | null;
	onContextSelect: (segmentId: number) => void;
	onSegmentRetranslate: (segmentId: number) => void;
}

export function SegmentsList({
	segments,
	selectedSegmentId,
	retranslatingSegmentId,
	onContextSelect,
	onSegmentRetranslate,
}: SegmentsListProps) {
	return (
		<Stack gap={5}>
			{segments.map((segment) => (
				<SegmentRow
					key={segment.segmentId}
					segment={segment}
					isSelected={selectedSegmentId === segment.segmentId}
					isRetranslating={retranslatingSegmentId === segment.segmentId}
					onContextSelect={onContextSelect}
					onRetranslate={onSegmentRetranslate}
				/>
			))}
		</Stack>
	);
}

interface SegmentRowProps {
	segment: TranslationSegmentRow;
	isSelected: boolean;
	isRetranslating: boolean;
	onContextSelect: (segmentId: number) => void;
	onRetranslate: (segmentId: number) => void;
}

const SegmentRow = memo(function SegmentRow({
	segment,
	isSelected,
	isRetranslating,
	onContextSelect,
	onRetranslate,
}: SegmentRowProps) {
	const srcText = segment.src || "";
	const tgtText =
		segment.text || (segment.status === "running" ? "Translating..." : "");
	const hasSource = srcText.trim().length > 0;
	const hasTarget = tgtText.trim().length > 0;

	if (!hasSource && !hasTarget) {
		return <Box height="2" />;
	}

	return (
		<Menu.Root>
			<Menu.ContextTrigger
				w="full"
				bg={isSelected ? "blue.50" : "transparent"}
				borderRadius="md"
				p={3}
				borderWidth={isSelected ? "1px" : "0px"}
				borderColor={isSelected ? "blue.200" : "transparent"}
				cursor="context-menu"
				onContextMenu={() => onContextSelect(segment.segmentId)}
			>
				<Stack gap={2}>
					{hasSource ? (
						<Text
							fontFamily="mono"
							whiteSpace="pre-wrap"
							color="gray.400"
							textAlign="left"
						>
							{srcText}
						</Text>
					) : null}
					{hasTarget ? (
						<Text whiteSpace="pre-wrap" color="gray.400" textAlign="left">
							{tgtText}
						</Text>
					) : null}
				</Stack>
			</Menu.ContextTrigger>
			<Portal>
				<Menu.Positioner>
					<Menu.Content>
						<Menu.Item
							value="retranslate"
							onClick={() => onRetranslate(segment.segmentId)}
							disabled={isRetranslating}
						>
							{isRetranslating ? "Retranslating..." : "Retranslate Segment"}
						</Menu.Item>
					</Menu.Content>
				</Menu.Positioner>
			</Portal>
		</Menu.Root>
	);
});
