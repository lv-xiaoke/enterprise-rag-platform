import { useCallback, useEffect, useState } from "react";
import { errorText, isAbort, json } from "./api";
export function useResource<T>(path: string | null, poll = false) {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((n) => n + 1), []);
  useEffect(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setLoading(true);
    setError("");
    const load = async () => {
      try {
        const result = await json<T>(path, { signal: controller.signal });
        if (!controller.signal.aborted) {
          setData(result);
          setError("");
        }
      } catch (e) {
        if (!controller.signal.aborted && !isAbort(e)) setError(errorText(e));
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          if (poll) timer = setTimeout(load, 1800);
        }
      }
    };
    void load();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, revision, poll]);
  return { data, loading, error, reload };
}
export function useHashRoute() {
  const [route, setRoute] = useState(
    window.location.hash.slice(1) || "/knowledge-bases",
  );
  useEffect(() => {
    const changed = () =>
      setRoute(window.location.hash.slice(1) || "/knowledge-bases");
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  return route;
}
export function navigate(path: string) {
  window.location.hash = path;
}
