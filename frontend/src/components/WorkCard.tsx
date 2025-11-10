import { Box, Heading, Text } from "@chakra-ui/react";
import type { KeyboardEvent, MouseEvent } from "react";
import type { Work } from "../types/works";

interface WorkCardProps {
	work: Work;
	onSelect?: (workId: number) => void;
	href?: string;
}

export function WorkCard({ work, onSelect, href }: WorkCardProps) {
	const hasSelectHandler = Boolean(onSelect);
	const isInteractive = Boolean(hasSelectHandler || href);

	function handleClick(event: MouseEvent<HTMLDivElement | HTMLAnchorElement>) {
		if (!hasSelectHandler) {
			return;
		}
		if (event.metaKey || event.ctrlKey || event.button !== 0) {
			return;
		}
		event.preventDefault();
		onSelect(work.id);
	}

	function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
		if (!hasSelectHandler) {
			return;
		}
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			onSelect(work.id);
		}
	}

	return (
		<Box
			as={href ? "a" : undefined}
			href={href}
			borderRadius="lg"
			borderWidth="1px"
			p={4}
			cursor={isInteractive ? "pointer" : undefined}
			role={hasSelectHandler && !href ? "button" : undefined}
			tabIndex={hasSelectHandler && !href ? 0 : undefined}
			onClick={hasSelectHandler ? handleClick : undefined}
			onKeyDown={hasSelectHandler ? handleKeyDown : undefined}
			transition="transform 0.15s ease"
			_hover={
				isInteractive
					? { transform: "translateY(-2px)", borderColor: "teal.300" }
					: undefined
			}
		>
			<Heading size="md" mb={2}>
				{work.title}
			</Heading>
			<Text fontSize="sm" color="gray.400">
				#{work.id}
			</Text>
		</Box>
	);
}
