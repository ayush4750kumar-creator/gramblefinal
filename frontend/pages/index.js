import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import Feed from '../components/Feed';
import RightSidebar from '../components/RightSidebar';

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
  const [user, setUser] = useState(null);
  const [view, setView] = useState('feed');
  const [watchlist, setWatchlist] = useState([]);
  const isMobile = useIsMobile();

  const onWatchlist = (symbol) => {
    setWatchlist(prev =>
      prev.find(w => w.symbol === symbol)
        ? prev.filter(w => w.symbol !== symbol)
        : [...prev, { symbol }]
    );
  };

  if (isMobile) {
    return (
      <div style={{ height: '100vh', overflow: 'hidden', background: '#f3f4f6', display: 'flex', flexDirection: 'column' }}>

       {/* MOBILE NAVBAR */}
<div style={{
  background: '#fff',
  borderBottom: '1px solid #e5e7eb',
  padding: '10px 14px',
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  flexShrink: 0,
  zIndex: 20,
}}>

  {/* Row 1: Logo + Search + Account — all in one line */}
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <span
      onClick={() => setView('feed')}
      style={{ fontSize: 22, fontWeight: 900, color: '#111', letterSpacing: '-0.5px', cursor: 'pointer', fontFamily: 'Georgia, serif', flexShrink: 0 }}
    >
      gramble<span style={{ color: '#2563eb' }}>.in</span>
    </span>

    {/* Search — grows to fill space between logo and account */}
    <div style={{ position: 'relative', flex: 1 }}>
      <span style={{
        position: 'absolute', left: 9, top: '50%',
        transform: 'translateY(-50%)', fontSize: 12, color: '#9ca3af'
      }}>🔍</span>
      <input
        placeholder="Search equity..."
        style={{
          width: '100%', padding: '7px 10px 7px 28px',
          borderRadius: 24, border: '1.5px solid #e5e7eb',
          fontSize: 12, background: '#f9fafb', color: '#111',
          outline: 'none', boxSizing: 'border-box',
        }}
        onChange={e => {
          const q = e.target.value.trim().toUpperCase();
          if (q.length >= 1) setView({ type: 'stock', symbol: q });
          else setView('feed');
        }}
      />
    </div>

    {user ? (
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        background: '#2563eb', color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 700, flexShrink: 0,
      }}>
        {(user.name || user.email || 'U')[0].toUpperCase()}
      </div>
    ) : (
      <button
        onClick={() => alert('Login coming soon')}
        style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '7px 12px', borderRadius: 20,
          border: '1.5px solid #2563eb', background: '#fff',
          color: '#2563eb', fontSize: 12, fontWeight: 600, cursor: 'pointer',
          flexShrink: 0,
        }}
      >
        <span>👤</span> Account
      </button>
    )}
  </div>

  {/* Row 2: Watchlist chips */}
  <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }}>
    {/* ...your existing watchlist chips... */}
  </div>
</div>
          {/* Row 2: Search pill */}
          <div style={{ position: 'relative' }}>
            <span style={{
              position: 'absolute', left: 12, top: '50%',
              transform: 'translateY(-50%)', fontSize: 14, color: '#9ca3af'
            }}>🔍</span>
            <input
              placeholder="Search an equity, index..."
              style={{
                width: '100%', padding: '9px 14px 9px 34px',
                borderRadius: 24, border: '1.5px solid #e5e7eb',
                fontSize: 13, background: '#f9fafb', color: '#111',
                outline: 'none', boxSizing: 'border-box',
              }}
              onChange={e => {
                const q = e.target.value.trim().toUpperCase();
                if (q.length >= 1) setView({ type: 'stock', symbol: q });
                else setView('feed');
              }}
            />
          </div>

          {/* Row 3: Watchlist chips */}
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }}>
            <button
              onClick={() => setView('feed')}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '6px 16px', borderRadius: 24, fontSize: 13, fontWeight: 700,
                background: view === 'feed' ? '#111' : '#f3f4f6',
                color: view === 'feed' ? '#fff' : '#374151',
                border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
              }}
            >
              Global
            </button>

            {watchlist.map(w => (
              <button
                key={w.symbol}
                onClick={() => setView({ type: 'stock', symbol: w.symbol })}
                style={{
                  padding: '6px 16px', borderRadius: 24, fontSize: 13, fontWeight: 700,
                  background: view?.symbol === w.symbol ? '#111' : '#f3f4f6',
                  color: view?.symbol === w.symbol ? '#fff' : '#374151',
                  border: 'none', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                }}
              >
                {w.symbol}
              </button>
            ))}

            
          </div>
        </div>

        {/* Feed */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <Feed user={user} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateRows: '58px 1fr', height: '100vh', overflow: 'hidden', background: '#f3f4f6' }}>
      <Navbar user={user} onLogin={setUser} onLogoClick={() => setView('feed')} />
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 300px', overflow: 'hidden', height: '100%', gap: 10, padding: 10 }}>
        <LeftSidebar user={user} watchlist={watchlist} setView={setView} view={view} onWatchlist={onWatchlist} />
        <Feed user={user} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        <RightSidebar setView={setView} />
      </div>
    </div>
  );
}