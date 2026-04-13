export type FacetType =
	| "overview"
	| "vocabulary"
	| "grammar"
	| "translation_logic";

export const FACET_ORDER: FacetType[] = [
	"overview",
	"vocabulary",
	"grammar",
	"translation_logic",
];

export const FACET_LABELS: Record<FacetType, string> = {
	overview: "Overview",
	vocabulary: "Vocabulary",
	grammar: "Grammar",
	translation_logic: "Logic",
};

export type FacetStatus = "pending" | "generating" | "complete" | "error";

export interface OverviewData {
	summary: string;
	tone?: string | null;
}

export interface VocabularyItemData {
	surface: string;
	reading?: string | null;
	gloss: string;
	part_of_speech?: string | null;
	nuance?: string | null;
	translation_type?: "literal" | "adaptive" | "idiomatic" | null;
	source_span_start?: number | null;
	source_span_end?: number | null;
}

export interface VocabularyData {
	items: VocabularyItemData[];
}

export interface GrammarPointData {
	source_snippet: string;
	label: string;
	explanation: string;
	sentence_effect: string;
	source_span_start?: number | null;
	source_span_end?: number | null;
}

export interface GrammarData {
	points: GrammarPointData[];
}

export interface TranslationLogicData {
	literal_sense: string;
	chosen_rendering: string;
	deviation_rationale?: string | null;
	tone_tradeoff?: string | null;
	alternate?: string | null;
}

export type FacetDataMap = {
	overview: OverviewData;
	vocabulary: VocabularyData;
	grammar: GrammarData;
	translation_logic: TranslationLogicData;
};

export interface FacetState<K extends FacetType = FacetType> {
	status: FacetStatus;
	data: FacetDataMap[K] | null;
	error: string | null;
}

export type FacetsState = {
	[K in FacetType]: FacetState<K>;
};

export function emptyFacets(): FacetsState {
	return {
		overview: { status: "pending", data: null, error: null },
		vocabulary: { status: "pending", data: null, error: null },
		grammar: { status: "pending", data: null, error: null },
		translation_logic: { status: "pending", data: null, error: null },
	};
}
