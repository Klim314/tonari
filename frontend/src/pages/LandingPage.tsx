import { useState } from "react";
import { AddWorkModal } from "../components/AddWorkModal";
import { type Domain, LandingLayout } from "../components/LandingLayout";
import { LandingWorksPane } from "../components/LandingWorksPane";
import { PromptsLandingPane } from "../components/PromptsLandingPane";

interface LandingPageProps {
	activeDomain: Domain;
	onDomainChange: (domain: Domain) => void;
	onSelectWork: (workId: number) => void;
}

export function LandingPage({
	activeDomain,
	onDomainChange,
	onSelectWork,
}: LandingPageProps) {
	const [isAddModalOpen, setAddModalOpen] = useState(false);

	return (
		<>
			<LandingLayout
				activeDomain={activeDomain}
				onDomainChange={onDomainChange}
				onNewWork={
					activeDomain === "works" ? () => setAddModalOpen(true) : undefined
				}
			>
				{activeDomain === "works" ? (
					<LandingWorksPane onSelectWork={onSelectWork} />
				) : activeDomain === "prompts" ? (
					<PromptsLandingPane />
				) : null}
			</LandingLayout>
			<AddWorkModal
				isOpen={isAddModalOpen}
				onClose={() => setAddModalOpen(false)}
				onImported={() => {
					// Works list will auto-refresh via query change
				}}
			/>
		</>
	);
}
