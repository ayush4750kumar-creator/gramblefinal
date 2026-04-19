export default function LeftSidebar({ user, watchlist = [], onRemove }) {
  return (
    <aside style={{ background:'#fff', borderRadius:12, border:'1px solid #e5e7eb', padding:16, overflowY:'auto', display:'flex', flexDirection:'column', gap:20 }}>
      
      {/* User card */}
      <div style={{ background:'#1e2433', borderRadius:10, padding:'16px 14px', display:'flex', alignItems:'center', gap:12 }}>
        <div style={{ width:42, height:42, background:'#2563eb', borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, color:'#fff', fontSize:17, flexShrink:0 }}>
          {user ? user.email[0].toUpperCase() : 'U'}
        </div>
        <div>
          <div style={{ fontWeight:600, fontSize:15, color:'#fff' }}>{user ? user.email : 'User'}</div>
          <div style={{ fontSize:13, color:'#9ca3af', marginTop:2 }}>Trader</div>
        </div>
      </div>

      {/* Watchlist */}
      <div>
        <div style={{ fontSize:11, fontWeight:700, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'1px', marginBottom:10 }}>
          Watchlist {watchlist.length > 0 && <span style={{ color:'#2563eb' }}>({watchlist.length})</span>}
        </div>

        {watchlist.length === 0 && (
          <div style={{ fontSize:13, color:'#9ca3af', lineHeight:1.7 }}>
            Search and add stocks to track them here.
          </div>
        )}

        {watchlist.map(item => (
          <div key={item.symbol} style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'10px 12px', borderRadius:8, marginBottom:6,
            background:'#f9fafb', border:'1px solid #e5e7eb'
          }}>
            <div>
              <div style={{ fontWeight:700, fontSize:14, color:'#111' }}>{item.symbol}</div>
              <div style={{ fontSize:11, color:'#9ca3af', marginTop:2 }}>
                Added {new Date(item.addedAt).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
              </div>
            </div>
            <button
              onClick={() => onRemove(item.symbol)}
              style={{ background:'none', border:'none', cursor:'pointer', color:'#9ca3af', fontSize:16, padding:'2px 6px', borderRadius:4 }}
              title="Remove"
            >×</button>
          </div>
        ))}
      </div>
    </aside>
  );
}