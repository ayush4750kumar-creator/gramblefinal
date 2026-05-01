import { useState, useEffect, useRef } from 'react';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import Feed from '../components/Feed';
import RightSidebar from '../components/RightSidebar';
import LoginModal from '../components/LoginModal';

const API       = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
const PRICE_API = `${API}/api/price`;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  return isMobile;
}

// ── Tiny hook: fetch prices for a symbol list, refresh every 15s ──────────
function useStockPrices(symbols = []) {
  const [prices, setPrices] = useState({});
  const timerRef            = useRef(null);
  const key                 = symbols.slice().sort().join(',');

  useEffect(() => {
    if (!key) return;
    const syms = key.split(',').filter(Boolean);

    const fetch_ = async () => {
      try {
        const res  = await fetch(`${PRICE_API}?symbols=${syms.join(',')}`);
        const data = await res.json();
        if (data.success) setPrices(prev => ({ ...prev, ...data.data }));
      } catch (_) {}
    };

    fetch_();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(fetch_, 15_000);
    return () => clearInterval(timerRef.current);
  }, [key]);

  return prices;
}

// ── Price display component ───────────────────────────────────────────────
function PriceTag({ data, small }) {
  if (!data) return <span style={{ fontSize: small ? 10 : 11, color: '#c4c4c4', fontFamily: 'monospace' }}>—</span>;
  const { formatted, changePct, isUp } = data;
  const color = isUp ? '#16a34a' : '#dc2626';
  const sign  = isUp ? '+' : '';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
      <span style={{ fontSize: small ? 11 : 12, fontWeight: 700, color: '#111', fontFamily: 'monospace', letterSpacing: '-0.3px' }}>
        {formatted}
      </span>
      <span style={{ fontSize: small ? 9 : 10, fontWeight: 600, color, fontFamily: 'monospace' }}>
        {sign}{changePct.toFixed(2)}%
      </span>
    </div>
  );
}

export default function Home() {
  const [user,           setUser]           = useState(null);
  const [token,          setToken]          = useState(null);
  const [view,           setView]           = useState('feed');
  const [watchlist,      setWatchlist]      = useState([]);
  const [showLogin,      setShowLogin]      = useState(false);
  const [mobileQuery,    setMobileQuery]    = useState('');
  const [mobileSuggests, setMobileSuggests] = useState([]);
  const [showMobileDrop, setShowMobileDrop] = useState(false);

  const mobileSearchRef = useRef(null);
  const isMobile        = useIsMobile();

  // Live prices for watchlist chips (mobile) + search suggestions
  const watchlistSymbols  = watchlist.map(w => w.symbol);
  const suggestSymbols    = mobileSuggests.map(s => s.symbol);
  const allMobileSymbols  = [...new Set([...watchlistSymbols, ...suggestSymbols])];
  const mobilePrices      = useStockPrices(allMobileSymbols);

  // ── Restore session ──────────────────────────────────────────────────────
  useEffect(() => {
    const savedToken = localStorage.getItem('gramble_token');
    const savedUser  = localStorage.getItem('gramble_user');
    if (savedToken && savedUser) {
      try {
        const u = JSON.parse(savedUser);
        setUser(u);
        setToken(savedToken);
        loadWatchlist(savedToken);
      } catch (_) {
        localStorage.removeItem('gramble_token');
        localStorage.removeItem('gramble_user');
      }
    }
  }, []);

  // ── Close mobile dropdown on outside click ───────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (mobileSearchRef.current && !mobileSearchRef.current.contains(e.target)) {
        setShowMobileDrop(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Mobile search suggestions ────────────────────────────────────────────
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const url  = mobileQuery
          ? `${API}/api/search/suggest?q=${encodeURIComponent(mobileQuery)}`
          : `${API}/api/search/suggest`;
        const res  = await fetch(url);
        const data = await res.json();
        if (data.success) setMobileSuggests(data.data);
      } catch (_) {}
    }, 200);
    return () => clearTimeout(timer);
  }, [mobileQuery]);

  // ── Load watchlist ───────────────────────────────────────────────────────
  const loadWatchlist = async (t) => {
    try {
      const res  = await fetch(`${API}/api/watchlist`, { headers: { Authorization: `Bearer ${t}` } });
      const data = await res.json();
      if (data.success) setWatchlist(data.data);
    } catch (_) {}
  };

  const handleLogin  = (u, t) => { setUser(u); setToken(t); loadWatchlist(t); };
  const handleLogout = () => {
    localStorage.removeItem('gramble_token');
    localStorage.removeItem('gramble_user');
    setUser(null); setToken(null); setWatchlist([]);
  };

  // ── Watchlist toggle ─────────────────────────────────────────────────────
  const onWatchlist = async (stock, action) => {
    const sym        = (typeof stock === 'string' ? stock : stock.symbol).toUpperCase();
    const stockEntry = typeof stock === 'string' ? { symbol: sym } : stock;

    if (action === 'remove') {
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      return;
    }

    const exists = watchlist.find(w => w.symbol === sym);
    if (exists) {
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      if (user && token) {
        await fetch(`${API}/api/watchlist/${sym}`, {
          method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {});
      }
    } else {
      setWatchlist(prev => [...prev, stockEntry]);
      if (user && token) {
        try {
          const res  = await fetch(`${API}/api/watchlist`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body:    JSON.stringify({ symbol: sym }),
          });
          const data = await res.json();
          if (data.success) {
            setWatchlist(prev => prev.map(w =>
              w.symbol === sym ? { ...stockEntry, article_count: data.news?.length || 0 } : w
            ));
          }
        } catch (_) {}
      }
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // MOBILE LAYOUT
  // ─────────────────────────────────────────────────────────────────────────
  if (isMobile) {
    return (
      <div style={{ height: '100vh', overflow: 'hidden', background: '#f3f4f6', display: 'flex', flexDirection: 'column' }}>

        <div style={{ background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 10, flexShrink: 0, zIndex: 20 }}>

          {/* Row 1: Logo + Search + Account */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span onClick={() => setView('feed')}
              style={{ fontSize: 22, fontWeight: 900, color: '#111', letterSpacing: '-0.5px', cursor: 'pointer', flexShrink: 0 }}>
              gramble<span style={{ color: '#2563eb' }}>.in</span>
            </span>

            {/* Mobile search with dropdown */}
            <div ref={mobileSearchRef} style={{ position: 'relative', flex: 1 }}>
              <span style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: '#9ca3af', zIndex: 1 }}>🔍</span>
              <input
                placeholder="Search equity..."
                value={mobileQuery}
                onChange={e => setMobileQuery(e.target.value)}
                onFocus={() => { setShowMobileDrop(true); if (!mobileQuery) setMobileSuggests([]); }}
                onKeyDown={e => {
                  if (e.key === 'Enter' && mobileQuery.trim()) {
                    setView({ type: 'stock', symbol: mobileQuery.trim().toUpperCase() });
                    setMobileQuery('');
                    setShowMobileDrop(false);
                  }
                }}
                style={{ width: '100%', padding: '7px 10px 7px 28px', borderRadius: 24, border: '1.5px solid #e5e7eb', fontSize: 12, background: '#f9fafb', color: '#111', outline: 'none', boxSizing: 'border-box' }}
              />

              {/* Suggestions dropdown WITH live prices */}
              {showMobileDrop && mobileSuggests.length > 0 && (
                <div style={{ position: 'absolute', top: '110%', left: 0, right: 0, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', zIndex: 300, overflow: 'hidden', maxHeight: 320, overflowY: 'auto' }}>
                  <div style={{ padding: '6px 12px 2px', fontSize: 10, color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase' }}>
                    {mobileQuery ? 'Matches' : '🔥 Popular'}
                  </div>
                  {mobileSuggests.map(s => {
                    const priceData = mobilePrices[s.symbol] || null;
                    const watched   = !!watchlist.find(w => w.symbol === s.symbol);
                    // exchange badge colors
                    const exColors  = { NSE: '#7c3aed', BSE: '#ea580c', NASDAQ: '#2563eb', NYSE: '#16a34a' };
                    const exColor   = exColors[(s.exchange||'').toUpperCase()] || '#6b7280';

                    return (
                      <div key={s.symbol}
                        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', borderTop: '1px solid #f3f4f6', cursor: 'pointer' }}
                        onClick={() => { setView({ type: 'stock', symbol: s.symbol }); setMobileQuery(''); setShowMobileDrop(false); }}
                      >
                        {/* Avatar */}
                        <div style={{ width: 32, height: 32, borderRadius: 7, background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 10, color: '#2563eb', flexShrink: 0 }}>
                          {s.symbol.slice(0, 3)}
                        </div>

                        {/* Name + exchange */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <span style={{ fontWeight: 700, fontSize: 12, color: '#111' }}>{s.symbol}</span>
                            <span style={{ fontSize: 9, fontWeight: 700, color: exColor, background: `${exColor}18`, borderRadius: 4, padding: '1px 5px' }}>
                              {s.exchange}
                            </span>
                          </div>
                          <div style={{ fontSize: 10, color: '#6b7280', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</div>
                        </div>

                        {/* Live price */}
                        <div onClick={e => e.stopPropagation()} style={{ flexShrink: 0 }}>
                          <PriceTag data={priceData} small />
                        </div>

                        {/* Watch button */}
                        <button
                          onClick={e => { e.stopPropagation(); onWatchlist(s); }}
                          style={{ fontSize: 10, background: watched ? '#dcfce7' : '#eff6ff', color: watched ? '#16a34a' : '#2563eb', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontWeight: 600, flexShrink: 0 }}
                        >
                          {watched ? '✓' : '+ Watch'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Account / Avatar */}
            {user ? (
              <div onClick={handleLogout} title="Tap to logout"
                style={{ width: 32, height: 32, borderRadius: '50%', background: '#2563eb', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, flexShrink: 0, cursor: 'pointer' }}>
                {(user.display_name || user.email || 'U')[0].toUpperCase()}
              </div>
            ) : (
              <button onClick={() => setShowLogin(true)}
                style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '7px 12px', borderRadius: 20, border: '1.5px solid #2563eb', background: '#fff', color: '#2563eb', fontSize: 12, fontWeight: 600, cursor: 'pointer', flexShrink: 0 }}>
                👤 Login
              </button>
            )}
          </div>

          {/* Row 2: Watchlist chips WITH live prices */}
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }}>
            <button onClick={() => setView('feed')}
              style={{ padding: '6px 16px', borderRadius: 24, fontSize: 13, fontWeight: 700, background: view === 'feed' ? '#111' : '#f3f4f6', color: view === 'feed' ? '#fff' : '#374151', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}>
              Global
            </button>

            {watchlist.map(w => {
              const active    = view?.symbol === w.symbol;
              const priceData = mobilePrices[w.symbol];
              const isUp      = priceData?.isUp ?? true;
              const pctColor  = priceData ? (isUp ? '#16a34a' : '#dc2626') : '#9ca3af';

              return (
                <button key={w.symbol}
                  onClick={() => setView({ type: 'stock', symbol: w.symbol })}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '5px 14px', borderRadius: 24, fontSize: 12, fontWeight: 700, background: active ? '#111' : '#f3f4f6', color: active ? '#fff' : '#374151', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0, gap: 1 }}
                >
                  <span>{w.symbol}</span>
                  {priceData && (
                    <span style={{ fontSize: 9, fontWeight: 600, color: active ? '#aaa' : pctColor, fontFamily: 'monospace' }}>
                      {priceData.formatted}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          <Feed user={user} token={token} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        </div>

        {showLogin && (
          <LoginModal
            onClose={() => setShowLogin(false)}
            onLogin={(u, t) => { handleLogin(u, t); setShowLogin(false); }}
          />
        )}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // DESKTOP LAYOUT
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'grid', gridTemplateRows: '58px 1fr', height: '100vh', overflow: 'hidden', background: '#f3f4f6' }}>
      <Navbar
        user={user}
        token={token}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onLogoClick={() => setView('feed')}
        setView={setView}
        watchlist={watchlist}
        onWatchlist={onWatchlist}
      />
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 300px', overflow: 'hidden', height: '100%', gap: 10, padding: 10 }}>
        <LeftSidebar user={user} token={token} watchlist={watchlist} setView={setView} view={view} onWatchlist={onWatchlist} />
        <Feed user={user} token={token} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        <RightSidebar setView={setView} />
      </div>
    </div>
  );
}