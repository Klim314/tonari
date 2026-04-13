import { Button, HStack, IconButton, Text } from "@chakra-ui/react";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";

interface ExplanationToolbarProps {
	segmentPosition: { index: number; total: number };
	sentencePosition: { index: number; total: number } | null;
	onPrevSentence: () => void;
	onNextSentence: () => void;
	canPrevSentence: boolean;
	canNextSentence: boolean;
	onRegenerate: () => void;
	isRegenerating: boolean;
	regenerateDisabled: boolean;
}

export function ExplanationToolbar({
	segmentPosition,
	sentencePosition,
	onPrevSentence,
	onNextSentence,
	canPrevSentence,
	canNextSentence,
	onRegenerate,
	isRegenerating,
	regenerateDisabled,
}: ExplanationToolbarProps) {
	return (
		<HStack
			justify="space-between"
			align="center"
			gap={3}
			flexWrap="wrap"
			w="full"
		>
			<HStack gap={4} fontSize="sm" color="fg.muted" flexWrap="wrap">
				<Text>
					<Text as="span" fontWeight="semibold" color="fg">
						Segment
					</Text>{" "}
					{segmentPosition.index + 1} / {segmentPosition.total}
				</Text>
				{sentencePosition ? (
					<HStack gap={1} align="center">
						<Text>
							<Text as="span" fontWeight="semibold" color="fg">
								Sentence
							</Text>{" "}
							{sentencePosition.index + 1} / {sentencePosition.total}
						</Text>
						<IconButton
							aria-label="Previous sentence"
							size="xs"
							variant="ghost"
							onClick={onPrevSentence}
							disabled={!canPrevSentence}
						>
							<ChevronLeft size={14} />
						</IconButton>
						<IconButton
							aria-label="Next sentence"
							size="xs"
							variant="ghost"
							onClick={onNextSentence}
							disabled={!canNextSentence}
						>
							<ChevronRight size={14} />
						</IconButton>
					</HStack>
				) : null}
			</HStack>

			<HStack gap={2}>
				<Button
					size="sm"
					variant="outline"
					onClick={onRegenerate}
					loading={isRegenerating}
					disabled={regenerateDisabled}
				>
					<RefreshCw size={14} />
					<Text>Regenerate</Text>
				</Button>
			</HStack>
		</HStack>
	);
}
