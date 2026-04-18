import { useState } from 'react';

export default function LoginModal({ onClose, onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name:'', email:'', password:'', confirm:'' });
  const [msg, setMsg] = useState('');

  const handle = async () => {
    if (mode === 'signup' && form.password !== form.confirm) return setMsg('Passwords do not match');
    setMsg(mode === 'login' ? 'Logging in...' : 'Account created! Check your email.');
    setTimeout(() => onLogin({ email: form.email }), 1000);
  };

  const overlay = { position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:999 };
  const box = { background:'#fff', borderRadius:12, padding:'32px 28px', width:360, position:'relative' };
  const inp = { width:'100%', border:'1px solid #e5e7eb', borderRadius:8, padding:'10px 14px', fontSize:14, marginBottom:12, background:'#f9fafb' };
  const btn = { width:'100%', background:'#3b82f6', color:'#fff', border:'none', borderRadius:8, padding:'11px', fontSize:14, fontWeight:600, cursor:'pointer' };

  return (
    <div style={overlay} onClick={onClose}>
      <div style={box} onClick={e => e.stopPropagation()}>
        <button onClick={onClose} style={{ position:'absolute', top:12, right:14, background:'none', border:'none', fontSize:18, cursor:'pointer', color:'#6b7280' }}>✕</button>
        <div style={{ textAlign:'center', marginBottom:20 }}>
          <div style={{ fontSize:18, fontWeight:700 }}>gramble<span style={{ color:'#3b82f6' }}>.in</span></div>
          <div style={{ color:'#6b7280', fontSize:13, marginTop:4 }}>{mode === 'login' ? 'Sign in to your account' : 'Create your account'}</div>
        </div>
        {mode === 'signup' && <input style={inp} placeholder="Full name" value={form.name} onChange={e => setForm({...form, name:e.target.value})} />}
        <input style={inp} placeholder="Email address" value={form.email} onChange={e => setForm({...form, email:e.target.value})} />
        <input style={inp} type="password" placeholder="Password" value={form.password} onChange={e => setForm({...form, password:e.target.value})} />
        {mode === 'signup' && <input style={inp} type="password" placeholder="Confirm password" value={form.confirm} onChange={e => setForm({...form, confirm:e.target.value})} />}
        {msg && <div style={{ color:'#3b82f6', fontSize:12, marginBottom:8, textAlign:'center' }}>{msg}</div>}
        <button style={btn} onClick={handle}>{mode === 'login' ? 'Log In' : 'Sign Up'}</button>
        <div style={{ textAlign:'center', marginTop:14, fontSize:13, color:'#6b7280' }}>
          {mode === 'login' ? <>No account? <span style={{ color:'#3b82f6', cursor:'pointer' }} onClick={() => setMode('signup')}>Sign up</span></> : <>Already have an account? <span style={{ color:'#3b82f6', cursor:'pointer' }} onClick={() => setMode('login')}>Log in</span></>}
        </div>
      </div>
    </div>
  );
}
