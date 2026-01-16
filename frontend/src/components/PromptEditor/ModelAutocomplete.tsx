import { Combobox, Portal, createListCollection } from "@chakra-ui/react";
import { useMemo } from "react";

interface ModelAutocompleteProps {
	value: string;
	onChange: (value: string) => void;
	models: string[];
	placeholder?: string;
	disabled?: boolean;
}

export function ModelAutocomplete({
	value,
	onChange,
	models,
	placeholder,
	disabled,
}: ModelAutocompleteProps) {
	const collection = useMemo(() => {
		return createListCollection({
			items: models.map((m) => ({ label: m, value: m })),
		});
	}, [models]);

	return (
		<Combobox.Root
			collection={collection}
			inputValue={value}
			onInputValueChange={(e) => onChange(e.inputValue)}
			disabled={disabled}
			inputBehavior="autocomplete"
		>
			<Combobox.Control>
				<Combobox.Input placeholder={placeholder} />
				<Combobox.IndicatorGroup>
					<Combobox.ClearTrigger />
					<Combobox.Trigger />
				</Combobox.IndicatorGroup>
			</Combobox.Control>

			<Portal>
				<Combobox.Positioner>
					<Combobox.Content
						bg="white"
						shadow="md"
						borderRadius="md"
						borderWidth="1px"
						borderColor="gray.200"
						maxH="200px"
						overflowY="auto"
						p={0}
						minW="100%"
						width="auto"
						zIndex={2000}
					>
						{collection.items.map((item) => (
							<Combobox.Item
								key={item.value}
								item={item}
								_hover={{ bg: "gray.100" }}
								cursor="pointer"
								px={3}
								py={2}
							>
								<Combobox.ItemText>{item.label}</Combobox.ItemText>
							</Combobox.Item>
						))}
					</Combobox.Content>
				</Combobox.Positioner>
			</Portal>
		</Combobox.Root>
	);
}
