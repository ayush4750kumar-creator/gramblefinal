import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import Feed from '../components/Feed';
import RightSidebar from '../components/RightSidebar';

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
  const [user,      setUser]      = useState(null);
  const [token,     setToken]     = useState(null);
  const [view,      setView]      = useState('feed');
  const [watchlist, setWatchlist] = useState([]);
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

  // ── Login handler ─────────────────────────────────────────────────────────
  const handleLogin = (u, t) => {
    setUser(u);
    setToken(t);
    loadWatchlist(t);
  };

  // ── Logout handler ────────────────────────────────────────────────────────
  const handleLogout = () => {
    setUser(null);
    setToken(null);
    setWatchlist([]);
  };

  // ── Add/remove watchlist item ─────────────────────────────────────────────
  const onWatchlist = async (symbol, action) => {
    const sym = symbol.toUpperCase();

    if (action === 'remove') {
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      return;
    }

    // Toggle
    const exists = watchlist.find(w => w.symbol === sym);
    if (exists) {
      // Remove
      setWatchlist(prev => prev.filter(w => w.symbol !== sym));
      if (user && token) {
        await fetch(`${API}/api/watchlist/${sym}`, {
          method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {});
      }
    } else {
      // Add — optimistic update first
      setWatchlist(prev => [...prev, { symbol: sym }]);
      if (user && token) {
        try {
          const res  = await fetch(`${API}/api/watchlist`, {
            method:  'POST',
            headers: { 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
            body:    JSON.stringify({ symbol: sym }),
          });
          const data = await res.json();
          // If backend returned article count, update item
          if (data.success) {
            setWatchlist(prev => prev.map(w => w.symbol === sym ? { ...w, article_count: data.news?.length || 0 } : w));
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
        <div style={{
          background:'#fff', borderBottom:'1px solid #e5e7eb',
          padding:'10px 14px', display:'flex', flexDirection:'column',
          gap:10, flexShrink:0, zIndex:20,
        }}>
          {/* Row 1: Logo + Search + Account */}
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span
              onClick={() => setView('feed')}
              style={{ fontSize:22, fontWeight:900, color:'#111', letterSpacing:'-0.5px', cursor:'pointer', fontFamily:'Georgia, serif', flexShrink:0 }}
            >gramble<span style={{ color:'#2563eb' }}>.in</span></span>

            <div style={{ position:'relative', flex:1 }}>
              <span style={{ position:'absolute', left:9, top:'50%', transform:'translateY(-50%)', fontSize:12, color:'#9ca3af' }}>🔍</span>
              <input
                placeholder="Search equity..."
                style={{ width:'100%', padding:'7px 10px 7px 28px', borderRadius:24, border:'1.5px solid #e5e7eb', fontSize:12, background:'#f9fafb', color:'#111', outline:'none', boxSizing:'border-box' }}
                onKeyDown={e => {
                  if (e.key === 'Enter' && e.target.value.trim()) {
                    setView({ type:'stock', symbol: e.target.value.trim().toUpperCase() });
                    e.target.value = '';
                  }
                }}
              />
            </div>

            {user ? (
              <div style={{ width:32, height:32, borderRadius:'50%', background:'#2563eb', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700, flexShrink:0 }}>
                {(user.display_name || user.email || 'U')[0].toUpperCase()}
              </div>
            ) : (
              <button
                onClick={() => {/* LoginModal handled in Navbar */}}
                style={{ display:'flex', alignItems:'center', gap:5, padding:'7px 12px', borderRadius:20, border:'1.5px solid #2563eb', background:'#fff', color:'#2563eb', fontSize:12, fontWeight:600, cursor:'pointer', flexShrink:0 }}
              >
                <span>👤</span> Account
              </button>
            )}
          </div>

          {/* Row 2: Watchlist chips */}
          <div style={{ display:'flex', gap:8, overflowX:'auto', paddingBottom:2 }}>
            <button
              onClick={() => setView('feed')}
              style={{ display:'flex', alignItems:'center', gap:5, padding:'6px 16px', borderRadius:24, fontSize:13, fontWeight:700, background: view === 'feed' ? '#111' : '#f3f4f6', color: view === 'feed' ? '#fff' : '#374151', border:'none', cursor:'pointer', whiteSpace:'nowrap', flexShrink:0 }}
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
      />
      <div style={{ display:'grid', gridTemplateColumns:'300px 1fr 300px', overflow:'hidden', height:'100%', gap:10, padding:10 }}>
        <LeftSidebar
          user={user}
          token={token}
          watchlist={watchlist}
          setView={setView}
          view={view}
          onWatchlist={onWatchlist}
        />
        <Feed
          user={user}
          token={token}
          view={view}
          setView={setView}
          onWatchlist={onWatchlist}
          watchlist={watchlist}
        />
        <RightSidebar setView={setView} />
      </div>
    </div>
  );
}