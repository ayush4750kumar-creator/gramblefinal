export default function LeftSidebar({ user }) {
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
        <div style={{ fontSize:13, color:'#9ca3af', lineHeight:1.7 }}>Search and add stocks to track them here.</div>
      </div>
    </aside>
  );
}
