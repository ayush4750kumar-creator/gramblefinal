import { useState } from 'react';
import LoginModal from './LoginModal';

export default function Navbar({ user, onLogin, onLogoClick }) {
  const [showLogin, setShowLogin] = useState(false);
  return (
    <>
      <header style={{ background:'#fff', borderBottom:'1px solid #e5e7eb', display:'flex', alignItems:'center', padding:'0 20px', height:58, gap:12, position:'sticky', top:0, zIndex:100 }}>
        <button onClick={onLogoClick} style={{ background:'none', border:'none', cursor:'pointer', padding:0, fontSize:22, fontWeight:800, color:'#111', letterSpacing:'-0.5px' }}>
          gramble<span style={{ color:'#3b82f6' }}>.in</span>
        </button>
        <input type="text" placeholder="Search any stock worldwide... AAPL, TSLA, RELIANCE"
          style={{ flex:1, maxWidth:460, background:'#f9fafb', border:'1px solid #e5e7eb', borderRadius:8, padding:'8px 14px', color:'#111', fontSize:14 }} />
        <nav style={{ display:'flex', gap:2 }}>
          {['F&O (Indian)','Screeners','Mutual Funds','More'].map(n => (
            <button key={n} style={{ background:'none', border:'none', color:'#374151', fontSize:14, padding:'6px 10px', borderRadius:6, cursor:'pointer', fontWeight:500 }}>{n} ▾</button>
          ))}
        </nav>
        <button onClick={() => !user && setShowLogin(true)}
          style={{ marginLeft:'auto', background:'#fff', border:'1px solid #e5e7eb', color:'#374151', padding:'7px 18px', borderRadius:8, fontSize:14, cursor:'pointer', fontWeight:500 }}>
          👤 {user ? user.email : 'Account'}
        </button>
      </header>
      {showLogin && <LoginModal onClose={() => setShowLogin(false)} onLogin={(u) => { onLogin(u); setShowLogin(false); }} />}
    </>
  );
}
