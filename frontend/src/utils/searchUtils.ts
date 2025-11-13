export type OptionItem = { value: string; label: any; key?: string };

export function createDebouncedFetcher(
  fetcher: (q: string, signal?: AbortSignal) => Promise<OptionItem[]>,
  setOptions: (opts: OptionItem[]) => void,
  cache: Map<string, OptionItem[]>,
  delay: number = 300
) {
  let timer: any = null;
  let ctrl: AbortController | null = null;

  return (prefix: string, q: string) => {
    const query = (q || '').trim();
    if (ctrl) ctrl.abort();
    if (timer) clearTimeout(timer);
    if (query.length < 2) {
      setOptions([]);
      return;
    }
    timer = setTimeout(async () => {
      const key = `${prefix}:${query}`;
      const hit = cache.get(key);
      if (hit) {
        setOptions(hit.map((o) => ({ ...o })));
        return;
      }
      ctrl = new AbortController();
      try {
        const opts = await fetcher(query, ctrl.signal);
        setOptions(opts);
        cache.set(key, opts);
      } catch {}
    }, delay);
  };
}
