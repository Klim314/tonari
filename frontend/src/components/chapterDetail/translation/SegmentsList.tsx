import {
	Box,
	Grid,
	HStack,
	IconButton,
	Menu,
	Portal,
	Stack,
	Text,
	Textarea,
} from "@chakra-ui/react";
import { Check, X } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { TranslationSegmentRow } from "../types";

interface SegmentsListProps {
	segments: TranslationSegmentRow[];
	selectedSegmentId: number | null;
	retranslatingSegmentId: number | null;
	editingSegmentId: number | null;
	onContextSelect: (segmentId: number) => void;
	onSegmentRetranslate: (segmentId: number) => void;
	onSegmentExplain: (segmentId: number) => void;
	onSegmentEditStart: (segmentId: number) => void;
	onSegmentEditSave: (segmentId: number, newText: string) => void;
	onSegmentEditCancel: () => void;
}

export function SegmentsList({
	segments,
	selectedSegmentId,
	retranslatingSegmentId,
	editingSegmentId,
	onContextSelect,
	onSegmentRetranslate,
	onSegmentExplain,
	onSegmentEditStart,
	onSegmentEditSave,
	onSegmentEditCancel,
}: SegmentsListProps) {
	return (
		<Stack gap={0}>
			{segments.map((segment) => (
				<SegmentRow
					key={segment.segmentId}
					segment={segment}
					isSelected={selectedSegmentId === segment.segmentId}
					isRetranslating={retranslatingSegmentId === segment.segmentId}
					isEditing={editingSegmentId === segment.segmentId}
					onContextSelect={onContextSelect}
					onRetranslate={onSegmentRetranslate}
					onExplain={onSegmentExplain}
					onEditStart={onSegmentEditStart}
					onEditSave={onSegmentEditSave}
					onEditCancel={onSegmentEditCancel}
				/>
			))}
		</Stack>
	);
}

interface SegmentRowProps {
	segment: TranslationSegmentRow;
	isSelected: boolean;
	isRetranslating: boolean;
	isEditing: boolean;
	onContextSelect: (segmentId: number) => void;
	onRetranslate: (segmentId: number) => void;
	onExplain: (segmentId: number) => void;
	onEditStart: (segmentId: number) => void;
	onEditSave: (segmentId: number, newText: string) => void;
	onEditCancel: () => void;
}

const SegmentRow = memo(function SegmentRow({
	segment,
	isSelected,
	isRetranslating,
	isEditing,
	onContextSelect,
	onRetranslate,
	onExplain,
	onEditStart,
	onEditSave,
	onEditCancel,
}: SegmentRowProps) {
	const srcText = segment.src || "";
	const tgtText =
		segment.text || (segment.status === "running" ? "Translating..." : "");
	const hasSource = srcText.trim().length > 0;
	const hasTarget = tgtText.trim().length > 0;
	const isFullyTranslated = segment.status === "completed" && hasTarget;
	const [menuOpen, setMenuOpen] = useState(false);
	const [contextMenuPos, setContextMenuPos] = useState<{
		x: number;
		y: number;
	}>({
		x: 0,
		y: 0,
	});
	const [editText, setEditText] = useState(segment.text || "");
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	// Reset edit text when segment text changes or editing starts
	useEffect(() => {
		if (isEditing) {
			setEditText(segment.text || "");
			// Focus textarea when editing starts
			setTimeout(() => textareaRef.current?.focus(), 0);
		}
	}, [isEditing, segment.text]);

	const handleSave = useCallback(() => {
		onEditSave(segment.segmentId, editText);
	}, [segment.segmentId, editText, onEditSave]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Escape") {
				onEditCancel();
			} else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
				handleSave();
			}
		},
		[onEditCancel, handleSave],
	);

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
						{isEditing ? (
							<Box>
								<HStack gap={2} mb={2} justify="space-between" align="center">
									<Text fontSize="xs" color="gray.400">
										Ctrl+Enter to save, Esc to cancel
									</Text>
									<HStack gap={1}>
										<IconButton
											aria-label="Cancel"
											size="xs"
											variant="ghost"
											onClick={onEditCancel}
										>
											<X size={14} />
										</IconButton>
										<IconButton
											aria-label="Save"
											size="xs"
											colorPalette="teal"
											onClick={handleSave}
										>
											<Check size={14} />
										</IconButton>
									</HStack>
								</HStack>
								<Textarea
									ref={textareaRef}
									value={editText}
									onChange={(e) => setEditText(e.target.value)}
									onKeyDown={handleKeyDown}
									fontSize="md"
									lineHeight="tall"
									minH="unset"
									overflow="hidden"
									resize="none"
									css={{
										fieldSizing: "content",
									}}
									autoFocus
								/>
							</Box>
						) : hasTarget ? (
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
							value="edit"
							onClick={() => onEditStart(segment.segmentId)}
							disabled={isRetranslating || isEditing}
						>
							Edit Translation
						</Menu.Item>
						<Menu.Item
							value="retranslate"
							onClick={() => onRetranslate(segment.segmentId)}
							disabled={isRetranslating || isEditing}
						>
							{isRetranslating ? "Retranslating..." : "Retranslate Segment"}
						</Menu.Item>
						<Menu.Item
							value="explain"
							onClick={() => onExplain(segment.segmentId)}
							disabled={!isFullyTranslated || isRetranslating || isEditing}
						>
							Explain Translation
						</Menu.Item>
					</Menu.Content>
				</Menu.Positioner>
			</Portal>
		</Menu.Root>
	);
});
