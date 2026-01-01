import { Box, Grid, Menu, Portal, Stack, Text } from "@chakra-ui/react";
import { memo, useState } from "react";
import type { TranslationSegmentRow } from "../types";

interface SegmentsListProps {
	segments: TranslationSegmentRow[];
	selectedSegmentId: number | null;
	retranslatingSegmentId: number | null;
	onContextSelect: (segmentId: number) => void;
	onSegmentRetranslate: (segmentId: number) => void;
	onSegmentExplain: (segmentId: number) => void;
}

export function SegmentsList({
	segments,
	selectedSegmentId,
	retranslatingSegmentId,
	onContextSelect,
	onSegmentRetranslate,
	onSegmentExplain,
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
					onExplain={onSegmentExplain}
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
	onExplain: (segmentId: number) => void;
}

const SegmentRow = memo(function SegmentRow({
	segment,
	isSelected,
	isRetranslating,
	onContextSelect,
	onRetranslate,
	onExplain,
}: SegmentRowProps) {
	const srcText = segment.src || "";
	const tgtText =
		segment.text || (segment.status === "running" ? "Translating..." : "");
	const hasSource = srcText.trim().length > 0;
	const hasTarget = tgtText.trim().length > 0;
	const [menuOpen, setMenuOpen] = useState(false);
	const [contextMenuPos, setContextMenuPos] = useState<{ x: number; y: number }>({
		x: 0,
		y: 0,
	});

	if (!hasSource && !hasTarget) {
		return <Box height="2" />;
	}

	const handleContextMenu = (e: React.MouseEvent<HTMLElement>) => {
		const selection = window.getSelection()?.toString() || "";

		// If text is selected, let the browser's default context menu show
		if (selection) {
			return;
		}

		// Prevent default and show our retranslate menu
		e.preventDefault();
		setContextMenuPos({ x: e.clientX, y: e.clientY });
		onContextSelect(segment.segmentId);
		setMenuOpen(true);
	};

	const getAnchorRect = () => {
		return {
			x: contextMenuPos.x,
			y: contextMenuPos.y,
			width: 0,
			height: 0,
		};
	};

	return (
		<Menu.Root
			open={menuOpen}
			onOpenChange={(details) => setMenuOpen(details.open)}
			positioning={{ getAnchorRect }}
		>
			<Box
				w="full"
				bg={isSelected ? "blue.50" : "transparent"}
				borderRadius="md"
				p={2}
				borderWidth={isSelected ? "1px" : "0px"}
				borderColor={isSelected ? "blue.200" : "transparent"}
				onContextMenu={handleContextMenu}
				_hover={{ bg: isSelected ? "blue.50" : "gray.50" }}
				transition="background 0.2s"
			>
				<Grid templateColumns="1fr 1fr" gap={6}>
					{/* Source Column */}
					<Box>
						<Text
							fontFamily="mono"
							whiteSpace="pre-wrap"
							color="gray.500"
							textAlign="left"
							fontSize="md"
							lineHeight="tall"
						>
							{srcText}
						</Text>
					</Box>

					{/* Target Column */}
					<Box borderLeftWidth="1px" borderLeftColor="gray.100" pl={6}>
						{hasTarget ? (
							<Text
								whiteSpace="pre-wrap"
								color="gray.800"
								textAlign="left"
								fontSize="md"
								lineHeight="tall"
							>
								{tgtText}
							</Text>
						) : (
							<Text color="gray.300" fontSize="sm" fontStyle="italic" pt={1}>
								{isRetranslating ? "Pending..." : "No translation"}
							</Text>
						)}
					</Box>
				</Grid>
			</Box>
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
						<Menu.Item
							value="explain"
							onClick={() => onExplain(segment.segmentId)}
							disabled={!hasTarget || isRetranslating}
						>
							Explain Translation
						</Menu.Item>
					</Menu.Content>
				</Menu.Positioner>
			</Portal>
		</Menu.Root>
	);
});
