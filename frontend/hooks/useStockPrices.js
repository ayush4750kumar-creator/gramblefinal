import { useState, useEffect, useRef, useCallback } from 'react';

const PRICE_API = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/price`
  : 'https://gramblefinal-production.up.railway.app/api/price';

const REFRESH_INTERVAL = 15_000;

export function useStockPrices(symbols = []) {
  const [prices, setPrices]   = useState({});
  const [loading, setLoading] = useState(false);
  const timerRef              = useRef(null);
  const symbolKey             = symbols.slice().sort().join(',');

  const fetchPrices = useCallback(async (syms) => {
    if (!syms.length) return;
    setLoading(true);
    try {
      const res  = await fetch(`${PRICE_API}?symbols=${syms.join(',')}`);
      const data = await res.json();
      if (data.success) setPrices(prev => ({ ...prev, ...data.data }));
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!symbolKey) return;
    const syms = symbolKey.split(',').filter(Boolean);
    fetchPrices(syms);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => fetchPrices(syms), REFRESH_INTERVAL);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [symbolKey, fetchPrices]);

  return { prices, loading };
}
