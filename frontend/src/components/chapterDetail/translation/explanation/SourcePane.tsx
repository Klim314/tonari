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
	/** Substrings within the active sentence to bold (e.g. grammar source_snippets) */
	highlights?: string[];
}

export function SourcePane({
	source,
	translation,
	sentences,
	activeSentenceIndex,
	highlights,
}: SourcePaneProps) {
	return (
		<Stack gap={4} w="full">
			<Section label="Source" isJapanese>
				{renderSourceWithHighlight(
					source,
					sentences,
					activeSentenceIndex,
					highlights,
				)}
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

/**
 * Render a string with bold markers around each occurrence of any highlight substring.
 * Returns an array of ReactNodes (plain strings and <Text fontWeight="bold"> spans).
 */
function renderWithBold(text: string, highlights: string[]): ReactNode[] {
	if (!highlights.length) return [text];

	// Build a sorted list of non-overlapping match ranges
	const ranges: { start: number; end: number }[] = [];
	for (const h of highlights) {
		if (!h) continue;
		let idx = text.indexOf(h);
		while (idx !== -1) {
			ranges.push({ start: idx, end: idx + h.length });
			idx = text.indexOf(h, idx + h.length);
		}
	}
	ranges.sort((a, b) => a.start - b.start);

	// Merge overlaps
	const merged: { start: number; end: number }[] = [];
	for (const r of ranges) {
		const last = merged[merged.length - 1];
		if (last && r.start <= last.end) {
			last.end = Math.max(last.end, r.end);
		} else {
			merged.push({ ...r });
		}
	}

	if (!merged.length) return [text];

	const parts: ReactNode[] = [];
	let cursor = 0;
	for (const { start, end } of merged) {
		if (cursor < start) parts.push(text.slice(cursor, start));
		parts.push(
			<Text as="span" fontWeight="bold" key={start}>
				{text.slice(start, end)}
			</Text>,
		);
		cursor = end;
	}
	if (cursor < text.length) parts.push(text.slice(cursor));
	return parts;
}

function renderSourceWithHighlight(
	source: string,
	sentences: SentenceRange[],
	activeIndex: number,
	highlights?: string[],
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

	const sentenceText = source.slice(start, end);
	const sentenceContent = highlights?.length
		? renderWithBold(sentenceText, highlights)
		: sentenceText;

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
				{sentenceContent}
			</Box>
			{source.slice(end)}
		</>
	);
}
