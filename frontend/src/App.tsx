import { useMemo } from "react";
import { WorksPage } from "./pages/WorksPage";
import { WorkDetailPage } from "./pages/WorkDetailPage";
import { ChapterDetailPage } from "./pages/ChapterDetailPage";
import { useBrowserLocation } from "./hooks/useBrowserLocation";

function App() {
	const { path, navigate } = useBrowserLocation();
	const pathname = useMemo(() => path.split("?")[0] ?? "/", [path]);
	const chapterDetailMatch = pathname.match(/^\/works\/(\d+)\/chapters\/(\d+)$/);
	const workDetailMatch = pathname.match(/^\/works\/(\d+)$/);

	if (chapterDetailMatch) {
		const workId = Number.parseInt(chapterDetailMatch[1] ?? "", 10);
		const chapterId = Number.parseInt(chapterDetailMatch[2] ?? "", 10);
		if (!Number.isNaN(workId) && !Number.isNaN(chapterId)) {
			return (
				<ChapterDetailPage
					workId={workId}
					chapterId={chapterId}
					onNavigateBack={(nextPath) => navigate(nextPath ?? `/works/${workId}`)}
				/>
			);
		}
	}

	if (workDetailMatch) {
		const workId = Number.parseInt(workDetailMatch[1] ?? "", 10);
		if (!Number.isNaN(workId)) {
			return (
				<WorkDetailPage
					workId={workId}
					onNavigateHome={() => navigate("/")}
					onNavigateToChapter={(chapterId) =>
						navigate(`/works/${workId}/chapters/${chapterId}`)
					}
				/>
			);
		}
	}

	return <WorksPage onSelectWork={(workId) => navigate(`/works/${workId}`)} />;
}

export default App;
