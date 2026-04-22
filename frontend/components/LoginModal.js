import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export default function LoginModal({ onClose, onLogin }) {
  const [mode,    setMode]    = useState('login');
  const [form,    setForm]    = useState({ name: '', email: '', password: '', confirm: '' });
  const [msg,     setMsg]     = useState('');
  const [loading, setLoading] = useState(false);

  const handle = async () => {
    setMsg('');
    if (!form.email || !form.password) return setMsg('Email and password are required');
    if (mode === 'signup' && form.password !== form.confirm) return setMsg('Passwords do not match');
    if (mode === 'signup' && form.password.length < 6)       return setMsg('Password must be at least 6 characters');

    setLoading(true);
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const body     = mode === 'login'
        ? { email: form.email, password: form.password }
        : { email: form.email, password: form.password, display_name: form.name };

      const res  = await fetch(`${API}${endpoint}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const data = await res.json();

      if (!res.ok) {
        setMsg(data.error || 'Something went wrong');
        setLoading(false);
        return;
      }

      // ✅ Persist token so user stays logged in on refresh
      localStorage.setItem('gramble_token', data.token);
      localStorage.setItem('gramble_user',  JSON.stringify(data.user));

      onLogin(data.user, data.token);
      onClose();
    } catch (err) {
      setMsg('Could not connect to server. Please try again.');
    }
    setLoading(false);
  };

  const overlay = { position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:999 };
  const box     = { background:'#fff', borderRadius:12, padding:'32px 28px', width:360, position:'relative' };
  const inp     = { width:'100%', border:'1px solid #e5e7eb', borderRadius:8, padding:'10px 14px', fontSize:14, marginBottom:12, background:'#f9fafb', boxSizing:'border-box', outline:'none' };
  const btn     = { width:'100%', background: loading ? '#93c5fd' : '#3b82f6', color:'#fff', border:'none', borderRadius:8, padding:'11px', fontSize:14, fontWeight:600, cursor: loading ? 'not-allowed' : 'pointer' };

  return (
    <div style={overlay} onClick={onClose}>
      <div style={box} onClick={e => e.stopPropagation()}>
        <button onClick={onClose} style={{ position:'absolute', top:12, right:14, background:'none', border:'none', fontSize:18, cursor:'pointer', color:'#6b7280' }}>✕</button>

        <div style={{ textAlign:'center', marginBottom:20 }}>
          <div style={{ fontSize:18, fontWeight:700 }}>gramble<span style={{ color:'#3b82f6' }}>.in</span></div>
          <div style={{ color:'#6b7280', fontSize:13, marginTop:4 }}>
            {mode === 'login' ? 'Sign in to your account' : 'Create your account'}
          </div>
        </div>

        {mode === 'signup' && (
          <input style={inp} placeholder="Full name (optional)"
            value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
        )}
        <input style={inp} placeholder="Email address" type="email"
          value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
          onKeyDown={e => e.key === 'Enter' && handle()} />
        <input style={inp} type="password" placeholder="Password"
          value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
          onKeyDown={e => e.key === 'Enter' && handle()} />
        {mode === 'signup' && (
          <input style={inp} type="password" placeholder="Confirm password"
            value={form.confirm} onChange={e => setForm({ ...form, confirm: e.target.value })}
            onKeyDown={e => e.key === 'Enter' && handle()} />
        )}

        {msg && (
          <div style={{ color:'#dc2626', fontSize:12, marginBottom:8, textAlign:'center' }}>{msg}</div>
        )}

        <button style={btn} onClick={handle} disabled={loading}>
          {loading ? 'Please wait...' : mode === 'login' ? 'Log In' : 'Sign Up'}
        </button>

        <div style={{ textAlign:'center', marginTop:14, fontSize:13, color:'#6b7280' }}>
          {mode === 'login'
            ? <>No account? <span style={{ color:'#3b82f6', cursor:'pointer' }} onClick={() => { setMode('signup'); setMsg(''); }}>Sign up</span></>
            : <>Already have? <span style={{ color:'#3b82f6', cursor:'pointer' }} onClick={() => { setMode('login'); setMsg(''); }}>Log in</span></>}
        </div>
      </div>
    </div>
  );
}