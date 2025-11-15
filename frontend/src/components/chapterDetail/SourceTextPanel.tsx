import { Box, Heading, Separator, Text } from "@chakra-ui/react";

interface SourceTextPanelProps {
	text: string;
}

export function SourceTextPanel({ text }: SourceTextPanelProps) {
	return (
		<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
			<Heading size="md" mb={4} h="8">
				Source Text
			</Heading>
			<Separator mb={4} />
			<Text
				whiteSpace="pre-wrap"
				fontFamily="mono"
				lineHeight="tall"
				color="gray.400"
			>
				{text}
			</Text>
		</Box>
	);
}
