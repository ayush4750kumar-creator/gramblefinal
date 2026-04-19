const categories = [
  { name:'Trending Today', desc:'Most active right now', badge:'LIVE', bc:'#dcfce7', tc:'#16a34a' },
  { name:'Top Gainers', desc:'Biggest movers up', badge:'TODAY', bc:'#dbeafe', tc:'#2563eb' },
  { name:'Top Losers', desc:'Biggest movers down', badge:'TODAY', bc:'#dbeafe', tc:'#2563eb' },
  { name:'Indian Index', desc:'Nifty · Sensex · BankNifty', badge:'NSE', bc:'#ede9fe', tc:'#7c3aed' },
  { name:'Gold', desc:'Spot & futures prices', badge:'MCX', bc:'#ffedd5', tc:'#ea580c' },
  { name:'Silver', desc:'Spot & futures prices', badge:'MCX', bc:'#ffedd5', tc:'#ea580c' },
  { name:'Top Indian Tech', desc:'TCS · Infy · Wipro & more', badge:'IT', bc:'#dbeafe', tc:'#2563eb' },
  { name:'Oil', desc:'Crude · ONGC · Reliance', badge:'CRUDE', bc:'#ffedd5', tc:'#ea580c' },
  { name:'Finance / Banks', desc:'HDFC · ICICI · SBI', badge:'BANK', bc:'#ede9fe', tc:'#7c3aed' },
  { name:'US Market', desc:'S&P · NASDAQ · Top Tech', badge:'NYSE', bc:'#dcfce7', tc:'#16a34a' },
];

const exchanges = [
  { key:'NSE',     label:'NSE',     desc:'National Stock Exchange', color:'#7c3aed', bg:'#ede9fe' },
  { key:'BSE',     label:'BSE',     desc:'Bombay Stock Exchange',   color:'#ea580c', bg:'#ffedd5' },
  { key:'NASDAQ',  label:'NASDAQ',  desc:'US Tech Exchange',        color:'#2563eb', bg:'#dbeafe' },
  { key:'NYSE',    label:'NYSE',    desc:'New York Stock Exchange',  color:'#16a34a', bg:'#dcfce7' },
  { key:'MCX',     label:'MCX',     desc:'Commodities Exchange',    color:'#d97706', bg:'#fef3c7' },
  { key:'CRYPTO',  label:'CRYPTO',  desc:'Digital Assets',          color:'#0891b2', bg:'#e0f2fe' },
];

export default function RightSidebar({ setView }) {
  return (
    <aside style={{ background:'#fff', borderRadius:12, border:'1px solid #e5e7eb', overflowY:'auto' }}>

      {/* World Markets Exchange Section */}
      <div style={{ padding:'14px 18px', borderBottom:'1px solid #e5e7eb' }}>
        <div style={{ fontWeight:700, fontSize:14, color:'#111', marginBottom:3 }}>WORLD MARKETS</div>
        <div style={{ fontSize:12, color:'#9ca3af', marginBottom:12 }}>Official exchange news</div>

        {exchanges.map(ex => (
          <div
            key={ex.key}
            onClick={() => setView(`market_${ex.key}`)}
            style={{
              display:'flex', alignItems:'center', justifyContent:'space-between',
              padding:'10px 14px', borderRadius:10, marginBottom:8,
              border:`1.5px solid ${ex.bg}`,
              background: ex.bg,
              cursor:'pointer', transition:'opacity 0.15s'
            }}
            onMouseEnter={e => e.currentTarget.style.opacity='0.8'}
            onMouseLeave={e => e.currentTarget.style.opacity='1'}
          >
            <div>
              <div style={{ fontSize:13, fontWeight:700, color: ex.color }}>{ex.label}</div>
              <div style={{ fontSize:11, color:'#6b7280', marginTop:1 }}>{ex.desc}</div>
            </div>
            <span style={{ color: ex.color, fontSize:16, fontWeight:700 }}>›</span>
          </div>
        ))}
      </div>

      {/* Category section */}
      <div style={{ padding:'14px 18px 6px', borderBottom:'1px solid #f3f4f6' }}>
        <div style={{ fontSize:11, fontWeight:700, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'1px' }}>Categories</div>
      </div>

      {categories.map(m => (
        <div key={m.name} onClick={() => setView(m.name)}
          style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'11px 18px', borderBottom:'1px solid #f3f4f6', cursor:'pointer' }}
          onMouseEnter={e => e.currentTarget.style.background='#f9fafb'}
          onMouseLeave={e => e.currentTarget.style.background='#fff'}>
          <div>
            <div style={{ fontSize:14, fontWeight:500, color:'#111', display:'flex', alignItems:'center', gap:6 }}>
              {m.name}
              <span style={{ fontSize:10, padding:'2px 7px', borderRadius:4, fontWeight:700, background:m.bc, color:m.tc }}>{m.badge}</span>
            </div>
            <div style={{ fontSize:12, color:'#9ca3af', marginTop:2 }}>{m.desc}</div>
          </div>
          <span style={{ color:'#d1d5db', fontSize:16 }}>›</span>
        </div>
      ))}
    </aside>
  );
}