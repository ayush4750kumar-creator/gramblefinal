import { useState, useRef, useEffect } from 'react';
import LoginModal from './LoginModal';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export default function Navbar({ user, token, onLogin, onLogout, onLogoClick, setView, watchlist = [], onWatchlist }) {
  const [showLogin,       setShowLogin]       = useState(false);
  const [query,           setQuery]           = useState('');
  const [suggestions,     setSuggestions]     = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target))
        setShowSuggestions(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch suggestions with debounce
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const res  = await fetch(`${API}/api/search/suggest?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        if (data.success) setSuggestions(data.data);
      } catch (_) {}
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const handleFocus = () => {
    setShowSuggestions(true);
    if (!query) {
      fetch(`${API}/api/search/suggest?q=`)
        .then(r => r.json())
        .then(d => { if (d.success) setSuggestions(d.data); })
        .catch(() => {});
    }
  };

  // Clicking a row opens the stock news
  const handleRowClick = (stock) => {
    setView({ type: 'stock', symbol: stock.symbol });
    setQuery('');
    setShowSuggestions(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('gramble_token');
    localStorage.removeItem('gramble_user');
    onLogout();
  };

  return (
    <>
      <header style={{
        background: '#fff', borderBottom: '1px solid #e5e7eb',
        display: 'flex', alignItems: 'center',
        padding: '0 20px', height: 58, gap: 12,
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <button onClick={onLogoClick} style={{ background:'none', border:'none', cursor:'pointer', padding:0, fontSize:22, fontWeight:800, color:'#111', letterSpacing:'-0.5px', flexShrink:0 }}>
          gramble<span style={{ color:'#3b82f6' }}>.in</span>
        </button>

        {/* ── Search bar ── */}
        <div ref={searchRef} style={{ position:'relative', flex:1, maxWidth:460 }}>
          <input
            type="text"
            placeholder="Search any stock worldwide... AAPL, TSLA, RELIANCE"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={handleFocus}
            onKeyDown={e => {
              if (e.key === 'Enter' && query.trim()) {
                setView({ type: 'stock', symbol: query.trim().toUpperCase() });
                setQuery('');
                setShowSuggestions(false);
              }
            }}
            style={{
              width: '100%', background: '#f9fafb',
              border: '1px solid #e5e7eb', borderRadius: 8,
              padding: '8px 14px', color: '#111', fontSize: 14,
              outline: 'none', boxSizing: 'border-box',
            }}
          />

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div style={{
              position: 'absolute', top: '110%', left: 0, right: 0,
              background: '#fff', border: '1px solid #e5e7eb',
              borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
              zIndex: 200, overflow: 'hidden',
            }}>
              <div style={{ padding: '8px 12px 4px', fontSize: 11, color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                {query ? 'Matches' : '🔥 Popular Stocks'}
              </div>

              {suggestions.map(s => {
                const inWatchlist = (watchlist || []).find(w => w.symbol === s.symbol);
                return (
                  <div
                    key={s.symbol}
                    onClick={() => handleRowClick(s)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '10px 14px', cursor: 'pointer',
                      borderTop: '1px solid #f3f4f6',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#f9fafb'}
                    onMouseLeave={e => e.currentTarget.style.background = '#fff'}
                  >
                    {/* Left: icon + name */}
                    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 8,
                        background: '#eff6ff', display:'flex', alignItems:'center',
                        justifyContent:'center', fontWeight:700, fontSize:11, color:'#2563eb',
                      }}>{s.symbol.slice(0, 3)}</div>
                      <div>
                        <div style={{ fontWeight:700, fontSize:13, color:'#111' }}>{s.symbol}</div>
                        <div style={{ fontSize:11, color:'#6b7280' }}>{s.name} · {s.exchange}</div>
                      </div>
                    </div>

                    {/* Right: article count + Add button */}
                    <div style={{ display:'flex', gap:6, alignItems:'center' }}>
                      {s.article_count > 0 && (
                        <span style={{ fontSize:10, color:'#6b7280', background:'#f3f4f6', padding:'2px 7px', borderRadius:20 }}>
                          {s.article_count} articles
                        </span>
                      )}
                      <button
                        onClick={e => {
                          e.stopPropagation(); // don't trigger row click
                          if (onWatchlist) onWatchlist(s.symbol);
                        }}
                        style={{
                          fontSize: 11,
                          background: inWatchlist ? '#dcfce7' : '#eff6ff',
                          color:      inWatchlist ? '#16a34a' : '#2563eb',
                          border: 'none', borderRadius: 6,
                          padding: '4px 10px', cursor: 'pointer', fontWeight: 700,
                        }}
                      >
                        {inWatchlist ? '✓ Added' : '+ Add'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <nav style={{ display:'flex', gap:2 }}>
          {['F&O (Indian)', 'Screeners', 'Mutual Funds', 'More'].map(n => (
            <button key={n} style={{ background:'none', border:'none', color:'#374151', fontSize:14, padding:'6px 10px', borderRadius:6, cursor:'pointer', fontWeight:500 }}>{n} ▾</button>
          ))}
        </nav>

        {user ? (
          <div style={{ display:'flex', alignItems:'center', gap:8, marginLeft:'auto' }}>
            <div style={{ width:32, height:32, borderRadius:'50%', background:'#2563eb', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700 }}>
              {(user.display_name || user.email || 'U')[0].toUpperCase()}
            </div>
            <button onClick={handleLogout} style={{ background:'none', border:'1px solid #e5e7eb', color:'#6b7280', padding:'5px 12px', borderRadius:8, fontSize:12, cursor:'pointer' }}>
              Logout
            </button>
          </div>
        ) : (
          <button onClick={() => setShowLogin(true)} style={{ marginLeft:'auto', background:'#fff', border:'1px solid #e5e7eb', color:'#374151', padding:'7px 18px', borderRadius:8, fontSize:14, cursor:'pointer', fontWeight:500 }}>
            👤 Account
          </button>
        )}
      </header>

      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onLogin={(u, t) => { onLogin(u, t); setShowLogin(false); }}
        />
      )}
    </>
  );
}