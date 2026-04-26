import { Box, HStack, Stack, Text } from "@chakra-ui/react";
import {
	FACET_LABELS,
	FACET_ORDER,
	type FacetsState,
	type FacetType,
} from "./types";

interface FacetRailProps {
	active: FacetType;
	onChange: (facet: FacetType) => void;
	facets: FacetsState;
	orientation?: "vertical" | "horizontal";
	statusLabel?: string;
}

export function FacetRail({
	active,
	onChange,
	facets,
	orientation = "vertical",
	statusLabel,
}: FacetRailProps) {
	const isHorizontal = orientation === "horizontal";
	const Container = isHorizontal ? HStack : Stack;

	return (
		<Stack gap={3} w="full" h="full">
			<Container
				gap={isHorizontal ? 2 : 1}
				align="stretch"
				w="full"
				overflowX={isHorizontal ? "auto" : undefined}
			>
				{FACET_ORDER.map((facetType) => {
					const isActive = facetType === active;
					const state = facets[facetType];
					return (
						<Box
							key={facetType}
							asChild
							textAlign="left"
							px={3}
							py={2}
							borderRadius="md"
							bg={isActive ? "bg.emphasized" : "transparent"}
							color={isActive ? "fg" : "fg.muted"}
							fontWeight={isActive ? "semibold" : "normal"}
							fontSize="sm"
							_hover={{ bg: isActive ? "bg.emphasized" : "bg.muted" }}
							transition="background 0.15s"
							whiteSpace="nowrap"
							flexShrink={0}
						>
							<button type="button" onClick={() => onChange(facetType)}>
								<HStack gap={2} justify="space-between" w="full">
									<Text as="span">{FACET_LABELS[facetType]}</Text>
									<FacetStatusGlyph status={state.status} />
								</HStack>
							</button>
						</Box>
					);
				})}
			</Container>
			{statusLabel && !isHorizontal ? (
				<Text fontSize="xs" color="fg.muted" px={3}>
					{statusLabel}
				</Text>
			) : null}
		</Stack>
	);
}

function FacetStatusGlyph({ status }: { status: string }) {
	if (status === "complete") {
		return (
			<Box as="span" w="6px" h="6px" borderRadius="full" bg="green.solid" />
		);
	}
	if (status === "error") {
		return <Box as="span" w="6px" h="6px" borderRadius="full" bg="red.solid" />;
	}
	return (
		<Box as="span" w="6px" h="6px" borderRadius="full" bg="border.emphasized" />
	);
}
