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
          gap: 8,
          flexShrink: 0,
          zIndex: 20,
        }}>

          {/* Row 1: App name + Account */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span
              onClick={() => setView('feed')}
              style={{ fontSize: 20, fontWeight: 800, color: '#111', letterSpacing: '-0.5px', cursor: 'pointer' }}
            >
              📈 Gramble
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {user ? (
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: '#2563eb', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 700,
                }}>
                  {(user.name || user.email || 'U')[0].toUpperCase()}
                </div>
              ) : (
                <button
                  onClick={() => alert('Login coming soon')}
                  style={{
                    padding: '6px 14px', borderRadius: 8,
                    background: '#2563eb', color: '#fff',
                    fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer',
                  }}
                >
                  Login
                </button>
              )}
            </div>
          </div>

          {/* Row 2: Search */}
          <div style={{ position: 'relative' }}>
            <span style={{
              position: 'absolute', left: 10, top: '50%',
              transform: 'translateY(-50%)', fontSize: 14, color: '#9ca3af'
            }}>🔍</span>
            <input
              placeholder="Search stocks, news..."
              style={{
                width: '100%', padding: '8px 12px 8px 32px',
                borderRadius: 10, border: '1px solid #e5e7eb',
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
          {watchlist.length > 0 && (
            <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 2 }}>
              {watchlist.map(w => (
                <button
                  key={w.symbol}
                  onClick={() => setView({ type: 'stock', symbol: w.symbol })}
                  style={{
                    padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                    background: view?.symbol === w.symbol ? '#2563eb' : '#eff6ff',
                    color: view?.symbol === w.symbol ? '#fff' : '#2563eb',
                    border: '1px solid #bfdbfe', cursor: 'pointer',
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}
                >
                  {w.symbol}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Feed */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <Feed user={user} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        </div>
      </div>
    );
  }

  // Desktop
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