import { useCallback, useEffect, useState } from "react";

function getCurrentPath() {
	if (typeof window === "undefined") {
		return "/";
	}
	return `${window.location.pathname}${window.location.search}`;
}

export function useBrowserLocation() {
	const [path, setPath] = useState<string>(() => getCurrentPath());

	useEffect(() => {
		function handlePopState() {
			setPath(getCurrentPath());
		}
		window.addEventListener("popstate", handlePopState);
		return () => {
			window.removeEventListener("popstate", handlePopState);
		};
	}, []);

	const navigate = useCallback(
		(nextPath: string) => {
			if (nextPath === path) {
				return;
			}
			window.history.pushState({}, "", nextPath);
			setPath(nextPath);
		},
		[path],
	);

	return { path, navigate };
}
