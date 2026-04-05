import { Box, Heading, Link, Text } from "@chakra-ui/react";
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
	const cardStyles = {
		borderRadius: "lg",
		borderWidth: "1px",
		borderColor: "gray.200",
		bg: "white",
		p: 4,
		cursor: isInteractive ? "pointer" : undefined,
		transition: "all 0.15s ease",
		_hover: isInteractive
			? {
					transform: "translateY(-2px)",
					borderColor: "teal.400",
					boxShadow: "md",
				}
			: undefined,
	} as const;

	function handleClick(event: MouseEvent<HTMLDivElement | HTMLAnchorElement>) {
		if (!hasSelectHandler) {
			return;
		}
		if (event.metaKey || event.ctrlKey || event.button !== 0) {
			return;
		}
		event.preventDefault();
		onSelect?.(work.id);
	}

	function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
		if (!hasSelectHandler) {
			return;
		}
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			onSelect?.(work.id);
		}
	}

	if (href) {
		return (
			<Link
				href={href}
				onClick={hasSelectHandler ? handleClick : undefined}
				{...cardStyles}
			>
				<Heading size="md" mb={2} color="gray.800">
					{work.title}
				</Heading>
				<Text fontSize="sm" color="gray.600">
					#{work.id}
				</Text>
			</Link>
		);
	}

	return (
		<Box
			role={hasSelectHandler && !href ? "button" : undefined}
			tabIndex={hasSelectHandler && !href ? 0 : undefined}
			onClick={hasSelectHandler ? handleClick : undefined}
			onKeyDown={hasSelectHandler ? handleKeyDown : undefined}
			{...cardStyles}
		>
			<Heading size="md" mb={2} color="gray.800">
				{work.title}
			</Heading>
			<Text fontSize="sm" color="gray.600">
				#{work.id}
			</Text>
		</Box>
	);
}
