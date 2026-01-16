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
		function handleLocationChange() {
			setPath(getCurrentPath());
		}
		window.addEventListener("popstate", handlePopState);
		window.addEventListener("locationchange", handleLocationChange);
		return () => {
			window.removeEventListener("popstate", handlePopState);
			window.removeEventListener("locationchange", handleLocationChange);
		};
	}, []);

	const navigate = useCallback(
		(nextPath: string) => {
			if (nextPath === path) {
				return;
			}
			window.history.pushState({}, "", nextPath);
			setPath(nextPath);
			window.dispatchEvent(new Event("locationchange"));
		},
		[path],
	);

	return { path, navigate };
}
