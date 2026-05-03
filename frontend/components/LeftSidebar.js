import { useState } from 'react';
import { useStockPrices } from '../hooks/useStockPrices';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

function PriceChip({ priceData }) {
  if (!priceData) return <span style={{ fontSize:11, color:'#9ca3af', background:'#f3f4f6', borderRadius:6, padding:'2px 7px', fontWeight:500, fontFamily:'monospace' }}>—</span>;
  const { formatted, changePct, isUp } = priceData;
  const sign  = isUp ? '+' : '';
  const color = isUp ? '#16a34a' : '#dc2626';
  const bg    = isUp ? '#dcfce7' : '#fee2e2';
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap:2 }}>
      <span style={{ fontSize:12, fontWeight:700, color:'#111', fontFamily:'monospace', letterSpacing:'-0.3px' }}>{formatted}</span>
      <span style={{ fontSize:10, fontWeight:600, color, background:bg, borderRadius:4, padding:'1px 5px', fontFamily:'monospace' }}>{sign}{changePct.toFixed(2)}%</span>
    </div>
  );
}

export default function LeftSidebar({ user, token, watchlist, setView, view, onWatchlist }) {
  const [editMode, setEditMode] = useState(false);
  const symbols = watchlist.map(w => w.symbol);
  const { prices } = useStockPrices(symbols);

  const handleRemove = async (symbol) => {
    onWatchlist(symbol, 'remove');
    if (user && token) {
      try {
        await fetch(`${API}/api/watchlist/${symbol}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch (_) {}
    }
  };

  return (
    <aside style={{ background:'#fff', borderRadius:12, border:'1px solid #e5e7eb', padding:16, overflowY:'auto', display:'flex', flexDirection:'column', gap:20 }}>

      {/* User card */}
      <div style={{ background:'#1e2433', borderRadius:10, padding:'16px 14px', display:'flex', alignItems:'center', gap:12 }}>
        <div style={{ width:42, height:42, background:'#2563eb', borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, color:'#fff', fontSize:17, flexShrink:0 }}>
          {user ? (user.display_name || user.email || 'U')[0].toUpperCase() : 'U'}
        </div>
        <div>
          <div style={{ fontWeight:600, fontSize:15, color:'#fff' }}>{user ? (user.display_name || user.email) : 'User'}</div>
          <div style={{ fontSize:13, color:'#9ca3af', marginTop:2 }}>Trader</div>
        </div>
      </div>

      {/* Watchlist */}
      <div>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:10 }}>
          <div style={{ fontSize:11, fontWeight:700, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'1px' }}>Watchlist</div>
          {watchlist.length > 0 && (
            <button onClick={() => setEditMode(!editMode)} style={{ background:'none', border:'none', fontSize:11, color: editMode ? '#dc2626' : '#9ca3af', cursor:'pointer', fontWeight:600, padding:0 }}>
              {editMode ? 'Done' : 'Remove'}
            </button>
          )}
        </div>

        {watchlist.length === 0 ? (
          <div style={{ fontSize:13, color:'#9ca3af', lineHeight:1.7 }}>Search and add stocks to track them here.</div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {watchlist.map(w => {
              // active if we're on news OR dashboard for this symbol
              const active    = (view?.type === 'stock' || view?.type === 'stock-news') && view?.symbol === w.symbol;
              const priceData = prices[w.symbol] || null;
              return (
                <div
                  key={w.symbol}
                  onClick={() => {
                    if (!editMode) {
                      // ── Opens NEWS FEED for this stock, not the dashboard ──
                      setView({ type: 'stock-news', symbol: w.symbol, companyName: w.name || w.symbol, exchange: w.exchange });
                    }
                  }}
                  style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 12px', borderRadius:8, cursor:'pointer', background: active ? '#eff6ff' : '#f9fafb', border: active ? '1px solid #bfdbfe' : '1px solid #e5e7eb', transition:'all 0.15s', gap:8 }}
                >
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ fontWeight:700, fontSize:14, color:'#2563eb', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{w.symbol}</div>
                    {w.exchange && <div style={{ fontSize:10, color:'#9ca3af', fontWeight:500, marginTop:1 }}>{w.exchange}</div>}
                  </div>
                  {editMode ? (
                    <span onClick={e => { e.stopPropagation(); handleRemove(w.symbol); }} style={{ fontSize:16, color:'#dc2626', cursor:'pointer', fontWeight:700, padding:'0 4px', lineHeight:1 }}>×</span>
                  ) : (
                    <PriceChip priceData={priceData} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}