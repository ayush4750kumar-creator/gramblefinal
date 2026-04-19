import { useState } from 'react';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import Feed from '../components/Feed';
import RightSidebar from '../components/RightSidebar';

export default function Home() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState('feed');
  const [watchlist, setWatchlist] = useState([]);

  const onWatchlist = (symbol) => {
    setWatchlist(prev =>
      prev.find(w => w.symbol === symbol)
        ? prev.filter(w => w.symbol !== symbol)
        : [...prev, { symbol }]
    );
  };

  return (
    <div style={{ display:'grid', gridTemplateRows:'58px 1fr', height:'100vh', overflow:'hidden', background:'#f3f4f6' }}>
      <Navbar user={user} onLogin={setUser} onLogoClick={() => setView('feed')} />
      <div style={{ display:'grid', gridTemplateColumns:'300px 1fr 300px', overflow:'hidden', height:'100%', gap:10, padding:10 }}>
        <LeftSidebar user={user} watchlist={watchlist} setView={setView} view={view} onWatchlist={onWatchlist} />
        <Feed user={user} view={view} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />
        <RightSidebar setView={setView} />
      </div>
    </div>
  );
}
