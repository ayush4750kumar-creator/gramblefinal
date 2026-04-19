import { useState } from 'react';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import Feed from '../components/Feed';
import RightSidebar from '../components/RightSidebar';

export default function Home() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState('feed');
  const [watchlist, setWatchlist] = useState([]);

  const addToWatchlist = async (symbol) => {
    if (watchlist.find(w => w.symbol === symbol)) return;
    const newItem = { symbol, addedAt: new Date().toISOString() };
    setWatchlist(prev => [...prev, newItem]);

    // Save to DB if user is logged in
    if (user) {
      try {
        await fetch('https://gramblefinal-production.up.railway.app/api/watchlist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId: user.id, symbol }),
        });
      } catch (e) {
        console.error('Watchlist save failed', e);
      }
    }
  };

  const removeFromWatchlist = (symbol) => {
    setWatchlist(prev => prev.filter(w => w.symbol !== symbol));
  };

  return (
    <div style={{ display:'grid', gridTemplateRows:'58px 1fr', height:'100vh', overflow:'hidden', background:'#f3f4f6' }}>
      <Navbar user={user} onLogin={setUser} onLogoClick={() => setView('feed')} />
      <div style={{ display:'grid', gridTemplateColumns:'370px 1fr 370px', overflow:'hidden', height:'100%', gap:10, padding:10 }}>
        <LeftSidebar user={user} watchlist={watchlist} onRemove={removeFromWatchlist} />
        <Feed user={user} view={view} setView={setView} onWatchlist={addToWatchlist} watchlist={watchlist} />
        <RightSidebar setView={setView} />
      </div>
    </div>
  );
}