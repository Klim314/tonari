import { Box, Stack, Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

export interface SentenceRange {
	span_start: number;
	span_end: number;
	text: string;
}

interface SourcePaneProps {
	source: string;
	translation: string;
	sentences: SentenceRange[];
	activeSentenceIndex: number;
}

export function SourcePane({
	source,
	translation,
	sentences,
	activeSentenceIndex,
}: SourcePaneProps) {
	return (
		<Stack gap={4} w="full">
			<Section label="Source" isJapanese>
				{renderSourceWithHighlight(source, sentences, activeSentenceIndex)}
			</Section>
			<Section label="Translation">
				<Text fontSize="md" lineHeight="1.7" color="fg">
					{translation || (
						<Text as="span" color="fg.muted" fontStyle="italic">
							(no translation)
						</Text>
					)}
				</Text>
			</Section>
		</Stack>
	);
}

function Section({
	label,
	isJapanese,
	children,
}: {
	label: string;
	isJapanese?: boolean;
	children: ReactNode;
}) {
	return (
		<Box>
			<Text
				fontSize="xs"
				textTransform="uppercase"
				fontWeight="bold"
				color="fg.muted"
				letterSpacing="wider"
				mb={2}
			>
				{label}
			</Text>
			<Box
				p={4}
				bg="bg.subtle"
				borderRadius="md"
				fontFamily={isJapanese ? "serif" : undefined}
				fontSize={isJapanese ? "lg" : "md"}
				lineHeight={isJapanese ? "1.9" : "1.7"}
				whiteSpace="pre-wrap"
			>
				{children}
			</Box>
		</Box>
	);
}

function renderSourceWithHighlight(
	source: string,
	sentences: SentenceRange[],
	activeIndex: number,
): ReactNode {
	if (!source) {
		return (
			<Text as="span" color="fg.muted" fontStyle="italic">
				(no source)
			</Text>
		);
	}

	const active = sentences[activeIndex];
	if (!active) {
		return source;
	}

	const start = Math.max(0, Math.min(active.span_start, source.length));
	const end = Math.max(start, Math.min(active.span_end, source.length));

	return (
		<>
			{source.slice(0, start)}
			<Box
				as="mark"
				bg="yellow.subtle"
				color="fg"
				px={1}
				py="1px"
				borderRadius="sm"
			>
				{source.slice(start, end)}
			</Box>
			{source.slice(end)}
		</>
	);
}
