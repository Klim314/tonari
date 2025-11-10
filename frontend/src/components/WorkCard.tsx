import { Box, Heading, Text } from '@chakra-ui/react';
import type { Work } from '../types/works';

interface WorkCardProps {
  work: Work;
}

export function WorkCard({ work }: WorkCardProps) {
  return (
    <Box borderRadius="lg" borderWidth="1px" p={4}>
      <Heading size="md" mb={2}>
        {work.title}
      </Heading>
      <Text fontSize="sm" >
        #{work.id}
      </Text>
    </Box>
  );
}
