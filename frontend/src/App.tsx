import { useMemo } from "react";
import { WorksPage } from "./pages/WorksPage";
import { WorkDetailPage } from "./pages/WorkDetailPage";
import { useBrowserLocation } from "./hooks/useBrowserLocation";

function App() {
	const { path, navigate } = useBrowserLocation();
	const pathname = useMemo(() => path.split("?")[0] ?? "/", [path]);
	const workDetailMatch = pathname.match(/^\/works\/(\d+)$/);

	if (workDetailMatch) {
		const workId = Number.parseInt(workDetailMatch[1] ?? "", 10);
		if (!Number.isNaN(workId)) {
			return (
				<WorkDetailPage workId={workId} onNavigateHome={() => navigate("/")} />
			);
		}
	}

	return <WorksPage onSelectWork={(workId) => navigate(`/works/${workId}`)} />;
}

export default App;
