import { Badge, Box, HStack, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { Loader } from "lucide-react";
import type { ReactNode } from "react";
import type {
	FacetState,
	FacetType,
	GrammarData,
	GrammarPointData,
	OverviewData,
	TranslationLogicData,
	VocabularyData,
	VocabularyItemData,
} from "./types";
import { FACET_LABELS } from "./types";

interface FacetContentProps {
	facetType: FacetType;
	state: FacetState;
}

export function FacetContent({ facetType, state }: FacetContentProps) {
	return (
		<Stack gap={4} w="full">
			<Text
				fontSize="xs"
				textTransform="uppercase"
				fontWeight="bold"
				color="fg.muted"
				letterSpacing="wider"
			>
				{FACET_LABELS[facetType]}
			</Text>
			<Body facetType={facetType} state={state} />
		</Stack>
	);
}

function Body({ facetType, state }: FacetContentProps) {
	if (state.status === "pending" || state.status === "generating") {
		return <Skeleton />;
	}
	if (state.status === "error") {
		return (
			<Box p={4} bg="red.subtle" color="red.fg" borderRadius="md" fontSize="sm">
				{state.error ?? "Generation failed."}
			</Box>
		);
	}
	if (!state.data) {
		return <EmptyState />;
	}

	switch (facetType) {
		case "overview":
			return <OverviewView data={state.data as OverviewData} />;
		case "vocabulary":
			return <VocabularyView data={state.data as VocabularyData} />;
		case "grammar":
			return <GrammarView data={state.data as GrammarData} />;
		case "translation_logic":
			return <TranslationLogicView data={state.data as TranslationLogicData} />;
	}
}

function Skeleton() {
	return (
		<HStack
			gap={3}
			p={4}
			bg="bg.subtle"
			borderRadius="md"
			color="fg.muted"
			fontSize="sm"
		>
			<Box as={Loader} boxSize="14px" animation="spin 1s linear infinite" />
			<Text>Analyzing...</Text>
		</HStack>
	);
}

function EmptyState() {
	return (
		<Text fontSize="sm" color="fg.muted" fontStyle="italic">
			No content yet.
		</Text>
	);
}

function Card({ children }: { children: React.ReactNode }) {
	return (
		<Box
			p={4}
			bg="bg"
			borderWidth="1px"
			borderColor="border.subtle"
			borderRadius="md"
		>
			{children}
		</Box>
	);
}

function OverviewView({ data }: { data: OverviewData }) {
	return (
		<Stack gap={3}>
			<Card>
				<Text fontSize="md" lineHeight="1.7" color="fg">
					{data.summary}
				</Text>
			</Card>
			{data.tone ? (
				<HStack gap={2} fontSize="sm" color="fg.muted">
					<Text fontWeight="semibold">Tone</Text>
					<Text>{data.tone}</Text>
				</HStack>
			) : null}
		</Stack>
	);
}

function VocabularyView({ data }: { data: VocabularyData }) {
	if (!data.items.length) {
		return <EmptyState />;
	}
	return (
		<SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
			{data.items.map((item) => (
				<VocabCard
					key={`${item.surface}|${item.reading ?? ""}|${item.source_span_start ?? ""}`}
					item={item}
				/>
			))}
		</SimpleGrid>
	);
}

function VocabCard({ item }: { item: VocabularyItemData }) {
	return (
		<Card>
			<Stack gap={1.5}>
				<HStack gap={2} align="baseline" flexWrap="wrap">
					<Text fontSize="lg" fontFamily="serif" fontWeight="semibold">
						{item.surface}
					</Text>
					{item.reading ? (
						<Text fontSize="sm" color="fg.muted" fontFamily="serif">
							{item.reading}
						</Text>
					) : null}
					{item.part_of_speech ? (
						<Badge size="sm" variant="subtle" colorPalette="gray">
							{item.part_of_speech}
						</Badge>
					) : null}
					{item.translation_type ? (
						<Badge size="sm" variant="subtle" colorPalette="blue">
							{item.translation_type}
						</Badge>
					) : null}
				</HStack>
				<Text fontSize="sm" color="fg">
					{item.gloss}
				</Text>
				{item.nuance ? (
					<Text fontSize="sm" color="fg.muted">
						{item.nuance}
					</Text>
				) : null}
			</Stack>
		</Card>
	);
}

function GrammarView({ data }: { data: GrammarData }) {
	if (!data.points.length) {
		return <EmptyState />;
	}
	return (
		<Stack gap={3}>
			{data.points.map((point) => (
				<GrammarCard
					key={`${point.label}|${point.source_snippet}|${point.source_span_start ?? ""}`}
					point={point}
				/>
			))}
		</Stack>
	);
}

function renderHighlighted(text: string, highlight: string): ReactNode[] {
	if (!highlight) return [text];
	const idx = text.indexOf(highlight);
	if (idx === -1) return [text];
	const parts: ReactNode[] = [];
	if (idx > 0) parts.push(text.slice(0, idx));
	parts.push(
		<Text as="span" fontWeight="bold" key={idx}>
			{highlight}
		</Text>,
	);
	if (idx + highlight.length < text.length)
		parts.push(text.slice(idx + highlight.length));
	return parts;
}

function GrammarCard({ point }: { point: GrammarPointData }) {
	return (
		<Card>
			<Stack gap={2}>
				<Badge size="sm" variant="subtle" colorPalette="purple" w="fit-content">
					{point.label}
				</Badge>
				<Text
					fontSize="md"
					fontFamily="serif"
					color="fg.muted"
					lineHeight="1.8"
				>
					{renderHighlighted(point.source_snippet, point.highlight)}
				</Text>
				<Text fontSize="sm" color="fg">
					{point.explanation}
				</Text>
				<Text fontSize="sm" color="fg.muted">
					<Text as="span" fontWeight="semibold">
						Effect:
					</Text>{" "}
					{point.sentence_effect}
				</Text>
			</Stack>
		</Card>
	);
}

function TranslationLogicView({ data }: { data: TranslationLogicData }) {
	return (
		<Stack gap={3}>
			<LabeledCard label="Literal sense">{data.literal_sense}</LabeledCard>
			<LabeledCard label="Chosen rendering">
				{data.chosen_rendering}
			</LabeledCard>
			{data.deviation_rationale ? (
				<LabeledCard label="Why this works">
					{data.deviation_rationale}
				</LabeledCard>
			) : null}
			{data.tone_tradeoff ? (
				<LabeledCard label="Tone tradeoff">{data.tone_tradeoff}</LabeledCard>
			) : null}
			{data.alternate ? (
				<LabeledCard label="Alternate rendering">{data.alternate}</LabeledCard>
			) : null}
		</Stack>
	);
}

function LabeledCard({
	label,
	children,
}: {
	label: string;
	children: React.ReactNode;
}) {
	return (
		<Card>
			<Stack gap={1.5}>
				<Text
					fontSize="xs"
					textTransform="uppercase"
					fontWeight="bold"
					color="fg.muted"
					letterSpacing="wider"
				>
					{label}
				</Text>
				<Text fontSize="sm" color="fg" lineHeight="1.7">
					{children}
				</Text>
			</Stack>
		</Card>
	);
}
