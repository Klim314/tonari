import { useState, useEffect, useRef } from "react";
import {
	Box,
	Input,
	Textarea,
	Heading,
	Text,
	VStack,
} from "@chakra-ui/react";

interface MetadataEditorProps {
	name: string;
	description: string;
	onNameChange: (name: string) => void;
	onDescriptionChange: (description: string) => void;
}

export function MetadataEditor({
	name,
	description,
	onNameChange,
	onDescriptionChange,
}: MetadataEditorProps) {
	const [isEditingName, setIsEditingName] = useState(false);
	const [isEditingDescription, setIsEditingDescription] = useState(false);
	const [editName, setEditName] = useState(name);
	const [editDescription, setEditDescription] = useState(description);
	const descriptionSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	useEffect(() => {
		setEditName(name);
	}, [name]);

	useEffect(() => {
		setEditDescription(description);
	}, [description]);

	const handleNameClick = () => {
		setEditName(name);
		setIsEditingName(true);
	};

	const handleNameBlur = () => {
		if (editName.trim() && editName !== name) {
			onNameChange(editName);
		} else {
			setEditName(name);
		}
		setIsEditingName(false);
	};

	const handleNameKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter") {
			handleNameBlur();
		} else if (e.key === "Escape") {
			setEditName(name);
			setIsEditingName(false);
		}
	};

	const handleDescriptionClick = () => {
		setEditDescription(description);
		setIsEditingDescription(true);
	};

	const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		const newDesc = e.target.value;
		setEditDescription(newDesc);

		// Debounce auto-save
		if (descriptionSaveTimeoutRef.current) {
			clearTimeout(descriptionSaveTimeoutRef.current);
		}

		descriptionSaveTimeoutRef.current = setTimeout(() => {
			if (newDesc !== description) {
				onDescriptionChange(newDesc);
			}
		}, 1000);
	};

	const handleDescriptionBlur = () => {
		if (editDescription !== description) {
			onDescriptionChange(editDescription);
		}
		setIsEditingDescription(false);
	};

	const handleDescriptionKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Escape") {
			setEditDescription(description);
			setIsEditingDescription(false);
		}
	};

	return (
		<Box
			borderWidth="1px"
			borderColor="whiteAlpha.200"
			borderRadius="md"
		>
			<VStack align="stretch" gap={2}>
				{/* Name */}
				{isEditingName ? (
					<Input
						value={editName}
						onChange={(e) => setEditName(e.target.value)}
						onBlur={handleNameBlur}
						onKeyDown={handleNameKeyDown}
						autoFocus
						placeholder="Enter prompt name"
						size="lg"
						fontWeight="bold"
					/>
				) : (
					<Heading size="lg" cursor="pointer" onClick={handleNameClick} _hover={{ opacity: 0.7 }}>
						{name}
					</Heading>
				)}

				{/* Description */}
				{isEditingDescription ? (
					<Textarea
						value={editDescription}
						onChange={handleDescriptionChange}
						onBlur={handleDescriptionBlur}
						onKeyDown={handleDescriptionKeyDown}
						autoFocus
						placeholder="Enter description (optional)"
						minH="60px"
						fontSize="sm"
					/>
				) : (
					<Text
						color={description ? "gray.300" : "gray.500"}
						fontSize="sm"
						cursor="pointer"
						onClick={handleDescriptionClick}
						_hover={{ opacity: 0.7 }}
						minH="20px"
					>
						{description || "Click to add description"}
					</Text>
				)}
			</VStack>
		</Box>
	);
}
