export default function LeftSidebar({ user, watchlist, setView, view, onWatchlist }) {
  return (
    <aside style={{ background:'#fff', borderRadius:12, border:'1px solid #e5e7eb', padding:16, overflowY:'auto', display:'flex', flexDirection:'column', gap:20 }}>
      <div style={{ background:'#1e2433', borderRadius:10, padding:'16px 14px', display:'flex', alignItems:'center', gap:12 }}>
        <div style={{ width:42, height:42, background:'#2563eb', borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, color:'#fff', fontSize:17, flexShrink:0 }}>
          {user ? user.email[0].toUpperCase() : 'U'}
        </div>
        <div>
          <div style={{ fontWeight:600, fontSize:15, color:'#fff' }}>{user ? user.email : 'User'}</div>
          <div style={{ fontSize:13, color:'#9ca3af', marginTop:2 }}>Trader</div>
        </div>
      </div>

      <div>
        <div style={{ fontSize:11, fontWeight:700, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'1px', marginBottom:10 }}>Watchlist</div>
        {watchlist.length === 0 ? (
          <div style={{ fontSize:13, color:'#9ca3af', lineHeight:1.7 }}>Search and add stocks to track them here.</div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {watchlist.map(w => {
              const active = view?.type === 'stock' && view?.symbol === w.symbol;
              return (
                <div key={w.symbol} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 12px', borderRadius:8, cursor:'pointer', background: active ? '#eff6ff' : '#f9fafb', border: active ? '1px solid #bfdbfe' : '1px solid #e5e7eb' }}>
                  <span onClick={() => setView({ type:'stock', symbol: w.symbol })} style={{ fontWeight:700, fontSize:14, color:'#2563eb', flex:1 }}>{w.symbol}</span>
                  <span onClick={() => onWatchlist(w.symbol)} style={{ fontSize:16, color:'#9ca3af', cursor:'pointer', padding:'0 4px' }} title="Remove">×</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
