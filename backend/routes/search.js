// frontend/src/components/SearchBar.js  (or wherever your search bar lives)
// This is a standalone search bar component. Integrate into your Header/Navbar.
// It fetches suggestions from your existing /api/search/suggest endpoint,
// then enriches them with live prices from /api/price.

import { useState, useRef, useEffect, useCallback } from 'react';

const SEARCH_API = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/search`
  : 'https://gramblefinal-production.up.railway.app/api/search';

const PRICE_API = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/price`
  : 'https://gramblefinal-production.up.railway.app/api/price';

// ── Exchange badge colors ─────────────────────────────────────────────────
const EXCHANGE_COLORS = {
  NSE:    { bg: '#ede9fe', color: '#7c3aed' },
  BSE:    { bg: '#fff7ed', color: '#ea580c' },
  NASDAQ: { bg: '#eff6ff', color: '#2563eb' },
  NYSE:   { bg: '#f0fdf4', color: '#16a34a' },
  UNKNOWN:{ bg: '#f3f4f6', color: '#6b7280' },
};

function ExchangeBadge({ exchange }) {
  const ex  = (exchange || 'UNKNOWN').toUpperCase().replace('NMS','NASDAQ').replace('NYQ','NYSE');
  const cfg = EXCHANGE_COLORS[ex] || EXCHANGE_COLORS.UNKNOWN;
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, padding: '2px 6px',
      borderRadius: 4, background: cfg.bg, color: cfg.color,
      letterSpacing: 0.4, flexShrink: 0,
    }}>
      {ex}
    </span>
  );
}

function LivePrice({ priceData, loading }) {
  if (loading) {
    return (
      <span style={{
        fontSize: 11, color: '#c4c4c4', fontFamily: 'monospace',
      }}>...</span>
    );
  }
  if (!priceData) return null;

  const { formatted, changePct, isUp } = priceData;
  const sign  = isUp ? '+' : '';
  const color = isUp ? '#16a34a' : '#dc2626';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
      <span style={{
        fontSize: 12, fontWeight: 700, color: '#111',
        fontFamily: 'monospace', letterSpacing: '-0.3px',
      }}>
        {formatted}
      </span>
      <span style={{
        fontSize: 10, fontWeight: 600, color,
        fontFamily: 'monospace',
      }}>
        {sign}{changePct.toFixed(2)}%
      </span>
    </div>
  );
}

export default function SearchBar({ onSelect, watchlist = [], onWatchlist }) {
  const [query,       setQuery]       = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [prices,      setPrices]      = useState({});
  const [priceLoading,setPriceLoading]= useState(false);
  const [open,        setOpen]        = useState(false);
  const [isPopular,   setIsPopular]   = useState(true);
  const [loading,     setLoading]     = useState(false);
  const [focused,     setFocused]     = useState(false);

  const inputRef    = useRef(null);
  const dropdownRef = useRef(null);
  const debounceRef = useRef(null);

  // Fetch prices for a list of symbols
  const fetchPrices = useCallback(async (symbols) => {
    if (!symbols.length) return;
    setPriceLoading(true);
    try {
      const res  = await fetch(`${PRICE_API}?symbols=${symbols.join(',')}`);
      const data = await res.json();
      if (data.success) setPrices(data.data || {});
    } catch (_) {}
    setPriceLoading(false);
  }, []);

  // Fetch suggestions (debounced)
  const fetchSuggestions = useCallback(async (q) => {
    setLoading(true);
    try {
      const url  = q ? `${SEARCH_API}/suggest?q=${encodeURIComponent(q)}` : `${SEARCH_API}/suggest`;
      const res  = await fetch(url);
      const data = await res.json();
      const list = data.data || [];
      setSuggestions(list);
      setIsPopular(data.popular || !q);
      setOpen(true);
      // Fetch prices for all returned symbols
      const syms = list.map(s => s.symbol).filter(Boolean);
      if (syms.length) fetchPrices(syms);
    } catch (_) {}
    setLoading(false);
  }, [fetchPrices]);

  // Debounce query changes
  useEffect(() => {
    if (!focused) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(query), query ? 250 : 0);
    return () => clearTimeout(debounceRef.current);
  }, [query, focused, fetchSuggestions]);

  // Load popular stocks on focus (when empty)
  const handleFocus = () => {
    setFocused(true);
    if (!query) fetchSuggestions('');
  };

  // Click outside to close
  useEffect(() => {
    const handler = (e) => {
      if (!dropdownRef.current?.contains(e.target) && !inputRef.current?.contains(e.target)) {
        setOpen(false);
        setFocused(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = (stock) => {
    setQuery('');
    setOpen(false);
    onSelect?.({ type: 'stock', symbol: stock.symbol });
  };

  const handleWatch = (e, symbol) => {
    e.stopPropagation();
    onWatchlist?.(symbol);
  };

  const isWatched = (symbol) => watchlist?.some(w => w.symbol === symbol);

  return (
    <div style={{ position: 'relative', flex: 1, maxWidth: 480 }}>
      {/* ── Input ─────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center',
        background: focused ? '#fff' : '#f3f4f6',
        border: focused ? '1.5px solid #2563eb' : '1.5px solid #e5e7eb',
        borderRadius: 10, padding: '0 12px',
        transition: 'all 0.15s', gap: 8,
      }}>
        <span style={{ fontSize: 15, color: '#9ca3af', flexShrink: 0 }}>🔍</span>
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={handleFocus}
          placeholder="Search any stock worldwide... AAPL, TSLA, RELIANCE"
          style={{
            flex: 1, border: 'none', background: 'transparent',
            outline: 'none', fontSize: 13, color: '#111',
            padding: '10px 0', fontFamily: 'inherit',
          }}
        />
        {loading && (
          <div style={{
            width: 14, height: 14, border: '2px solid #e5e7eb',
            borderTop: '2px solid #2563eb', borderRadius: '50%',
            animation: 'spin 0.7s linear infinite', flexShrink: 0,
          }} />
        )}
        {query && (
          <button onClick={() => { setQuery(''); inputRef.current?.focus(); }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: 16, padding: 0, lineHeight: 1 }}>
            ×
          </button>
        )}
      </div>

      {/* ── Dropdown ──────────────────────────────────────────────────── */}
      {open && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0,
            background: '#fff', border: '1px solid #e5e7eb',
            borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
            zIndex: 1000, overflow: 'hidden', maxHeight: 420, overflowY: 'auto',
          }}
        >
          {isPopular && (
            <div style={{
              padding: '10px 14px 6px', fontSize: 10, fontWeight: 700,
              color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              🔥 Popular Stocks
            </div>
          )}

          {suggestions.map((stock) => {
            const priceData = prices[stock.symbol];
            const watched   = isWatched(stock.symbol);

            return (
              <div
                key={stock.symbol}
                onClick={() => handleSelect(stock)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 14px', cursor: 'pointer',
                  transition: 'background 0.1s',
                  borderBottom: '1px solid #f3f4f6',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#f8faff'}
                onMouseLeave={e => e.currentTarget.style.background = '#fff'}
              >
                {/* Symbol avatar */}
                <div style={{
                  width: 34, height: 34, borderRadius: 8,
                  background: '#eff6ff', color: '#2563eb',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 800, fontSize: 10, flexShrink: 0, letterSpacing: 0,
                }}>
                  {stock.symbol.slice(0, 3)}
                </div>

                {/* Name + exchange */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, fontSize: 13, color: '#111' }}>{stock.symbol}</span>
                    <ExchangeBadge exchange={stock.exchange} />
                    {stock.article_count > 0 && (
                      <span style={{ fontSize: 10, color: '#9ca3af' }}>{stock.article_count} articles</span>
                    )}
                  </div>
                  <div style={{
                    fontSize: 11, color: '#6b7280', marginTop: 1,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {stock.name}
                  </div>
                </div>

                {/* Live price */}
                <div style={{ flexShrink: 0 }}>
                  <LivePrice priceData={priceData} loading={priceLoading && !priceData} />
                </div>

                {/* Watch button */}
                <button
                  onClick={(e) => handleWatch(e, stock.symbol)}
                  style={{
                    flexShrink: 0, padding: '5px 10px', borderRadius: 6,
                    fontSize: 11, fontWeight: 600, cursor: 'pointer', border: 'none',
                    background: watched ? '#2563eb' : '#f3f4f6',
                    color: watched ? '#fff' : '#374151',
                    transition: 'all 0.15s',
                  }}
                >
                  {watched ? '✓' : '+ Watch'}
                </button>
              </div>
            );
          })}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}