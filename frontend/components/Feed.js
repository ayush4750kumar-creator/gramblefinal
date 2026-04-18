export default function Feed({ user, view, setView }) {
  return (
    <main style={{ background:'#fff', borderRadius:12, border:'1px solid #e5e7eb', padding:'20px 24px', overflowY:'auto' }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:18, paddingBottom:14, borderBottom:'1px solid #e5e7eb' }}>
        {view !== 'feed' && (
          <button onClick={() => setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:18, color:'#6b7280', padding:0 }}>←</button>
        )}
        <div style={{ fontSize:20, fontWeight:700, color:'#111' }}>{view === 'feed' ? 'Global Feed' : view}</div>
      </div>
      <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'65%', gap:12 }}>
        <div style={{ fontSize:44 }}>📭</div>
        <div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No real news found yet</div>
        <div style={{ fontSize:13, color:'#9ca3af', textAlign:'center', lineHeight:1.7, maxWidth:280 }}>The agents are fetching live market news. Check back in a few minutes.</div>
      </div>
    </main>
  );
}
