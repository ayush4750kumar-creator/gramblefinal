import { useState, useEffect, useRef } from 'react';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import Feed from '../components/Feed';
import RightSidebar from '../components/RightSidebar';
import LoginModal from '../components/LoginModal';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

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

export default function Home() {
  const [user,            setUser]            = useState(null);
  const [token,           setToken]           = useState(null);
  const [view,            setView]            = useState('feed');
  const [watchlist,       setWatchlist]       = useState([]);
  const [showLogin,       setShowLogin]       = useState(false);
  const [mobileQuery,     setMobileQuery]     = useState('');
  const [mobileSuggests,  setMobileSuggests]  = useState([]);
  const [showMobileDrop,  setShowMobileDrop]  = useState(false);
  const mobileSearchRef = useRef(null);
  const isMobile = useIsMobile();

  // ── Restore session on page load ──────────────────────────────────────────
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

  // ── Close mobile dropdown on outside click ────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (mobileSearchRef.current && !mobileSearchRef.current.contains(e.target)) {
        setShowMobileDrop(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Fetch mobile search suggestions ──────────────────────────────────────
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const res  = await fetch(`${API}/api/search/suggest?q=${encodeURIComponent(mobileQuery)}`);
        const data = await res.json();
        if (data.success) setMobileSuggests(data.data);
      } catch (_) {}
    }, 200);
    return () => clearTimeout(timer);
  }, [mobileQuery]);

  // ── Load watchlist from backend ───────────────────────────────────────────
  const loadWatchlist = async (t) => {
    try {
      const res  = await fetch(`${API}/api/watchlist`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const data = await res.json();
      if (data.success) setWatchlist(data.data);
    } catch (_) {}
  };

  const handleLogin = (u, t) => {
    setUser(u);
    setToken(t);
    loadWatchlist(t);
  };

  const handleLogout = () => {
    localStorage.removeItem('gramble_token');
    localStorage.removeItem('gramble_user');
    setUser(null);
    setToken(null);
    setWatchlist([]);
  };

  // ── Watchlist toggle — accepts full stock object OR plain symbol string ───
  const onWatchlist = async (stock, action) => {
    const sym        = (typeof stock === 'string' ? stock : stock.symbol).toUpperCase();
    const stockEntry = typeof stock === 'string' ? { symbol: sym } : stock;

    if (action === 'remove') {
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      return;
    }

    const exists = watchlist.find(w => w.symbol === sym);
    if (exists) {
      // Toggle off — remove from local state + backend
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      if (user && token) {
        await fetch(`${API}/api/watchlist/${sym}`, {
          method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {});
      }
    } else {
      // Toggle on — optimistically add full object so name/exchange show in sidebar
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
      <div style={{ height:'100vh', overflow:'hidden', background:'#f3f4f6', display:'flex', flexDirection:'column' }}>

        <div style={{ background:'#fff', borderBottom:'1px solid #e5e7eb', padding:'10px 14px', display:'flex', flexDirection:'column', gap:10, flexShrink:0, zIndex:20 }}>

          {/* Row 1: Logo + Search + Account */}
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span onClick={() => setView('feed')}
              style={{ fontSize:22, fontWeight:900, color:'#111', letterSpacing:'-0.5px', cursor:'pointer', flexShrink:0 }}>
              gramble<span style={{ color:'#2563eb' }}>.in</span>
            </span>

            {/* Mobile search with dropdown */}
            <div ref={mobileSearchRef} style={{ position:'relative', flex:1 }}>
              <span style={{ position:'absolute', left:9, top:'50%', transform:'translateY(-50%)', fontSize:12, color:'#9ca3af', zIndex:1 }}>🔍</span>
              <input
                placeholder="Search equity..."
                value={mobileQuery}
                onChange={e => setMobileQuery(e.target.value)}
                onFocus={() => setShowMobileDrop(true)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && mobileQuery.trim()) {
                    setView({ type: 'stock', symbol: mobileQuery.trim().toUpperCase() });
                    setMobileQuery('');
                    setShowMobileDrop(false);
                  }
                }}
                style={{ width:'100%', padding:'7px 10px 7px 28px', borderRadius:24, border:'1.5px solid #e5e7eb', fontSize:12, background:'#f9fafb', color:'#111', outline:'none', boxSizing:'border-box' }}
              />

              {/* Suggestions dropdown */}
              {showMobileDrop && mobileSuggests.length > 0 && (
                <div style={{ position:'absolute', top:'110%', left:0, right:0, background:'#fff', border:'1px solid #e5e7eb', borderRadius:10, boxShadow:'0 8px 24px rgba(0,0,0,0.12)', zIndex:300, overflow:'hidden', maxHeight:280, overflowY:'auto' }}>
                  <div style={{ padding:'6px 12px 2px', fontSize:10, color:'#9ca3af', fontWeight:700, textTransform:'uppercase' }}>
                    {mobileQuery ? 'Matches' : '🔥 Popular'}
                  </div>
                  {mobileSuggests.map(s => (
                    <div key={s.symbol}
                      style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 12px', borderTop:'1px solid #f3f4f6', cursor:'pointer' }}
                      onClick={() => {
                        setView({ type: 'stock', symbol: s.symbol });
                        setMobileQuery('');
                        setShowMobileDrop(false);
                      }}
                    >
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <div style={{ width:32, height:32, borderRadius:7, background:'#eff6ff', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, fontSize:10, color:'#2563eb' }}>
                          {s.symbol.slice(0,3)}
                        </div>
                        <div>
                          <div style={{ fontWeight:700, fontSize:12, color:'#111' }}>{s.symbol}</div>
                          <div style={{ fontSize:10, color:'#6b7280' }}>{s.name}</div>
                        </div>
                      </div>
                      <div style={{ display:'flex', gap:6, alignItems:'center' }}>
                        <button
                          onClick={e => { e.stopPropagation(); onWatchlist(s); }}  // ← pass full object
                          style={{ fontSize:10, background: watchlist.find(w=>w.symbol===s.symbol) ? '#dcfce7' : '#eff6ff', color: watchlist.find(w=>w.symbol===s.symbol) ? '#16a34a' : '#2563eb', border:'none', borderRadius:6, padding:'3px 8px', cursor:'pointer', fontWeight:600 }}
                        >
                          {watchlist.find(w => w.symbol === s.symbol) ? '✓ Added' : '+ Watch'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Account / Avatar */}
            {user ? (
              <div
                onClick={handleLogout}
                title="Tap to logout"
                style={{ width:32, height:32, borderRadius:'50%', background:'#2563eb', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700, flexShrink:0, cursor:'pointer' }}
              >
                {(user.display_name || user.email || 'U')[0].toUpperCase()}
              </div>
            ) : (
              <button
                onClick={() => setShowLogin(true)}
                style={{ display:'flex', alignItems:'center', gap:5, padding:'7px 12px', borderRadius:20, border:'1.5px solid #2563eb', background:'#fff', color:'#2563eb', fontSize:12, fontWeight:600, cursor:'pointer', flexShrink:0 }}
              >
                👤 Login
              </button>
            )}
          </div>

          {/* Row 2: Watchlist chips */}
          <div style={{ display:'flex', gap:8, overflowX:'auto', paddingBottom:2 }}>
            <button onClick={() => setView('feed')}
              style={{ padding:'6px 16px', borderRadius:24, fontSize:13, fontWeight:700, background: view === 'feed' ? '#111' : '#f3f4f6', color: view === 'feed' ? '#fff' : '#374151', border:'none', cursor:'pointer', whiteSpace:'nowrap', flexShrink:0 }}
            >Global</button>

            {watchlist.map(w => (
              <button key={w.symbol}
                onClick={() => setView({ type:'stock', symbol: w.symbol })}
                style={{ padding:'6px 16px', borderRadius:24, fontSize:13, fontWeight:700, background: view?.symbol === w.symbol ? '#111' : '#f3f4f6', color: view?.symbol === w.symbol ? '#fff' : '#374151', border:'none', cursor:'pointer', whiteSpace:'nowrap', flexShrink:0 }}
              >{w.symbol}</button>
            ))}
          </div>
        </div>

        <div style={{ flex:1, overflowY:'auto' }}>
          <Feed user={user} token={token} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        </div>

        {/* Mobile login modal */}
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
    <div style={{ display:'grid', gridTemplateRows:'58px 1fr', height:'100vh', overflow:'hidden', background:'#f3f4f6' }}>
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
      <div style={{ display:'grid', gridTemplateColumns:'300px 1fr 300px', overflow:'hidden', height:'100%', gap:10, padding:10 }}>
        <LeftSidebar user={user} token={token} watchlist={watchlist} setView={setView} view={view} onWatchlist={onWatchlist} />
        <Feed user={user} token={token} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        <RightSidebar setView={setView} />
      </div>
    </div>
  );
}