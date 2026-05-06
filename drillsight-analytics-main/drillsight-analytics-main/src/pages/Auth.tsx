import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { login, register } from '@/api/ddrClient';
import { AlertCircle, Lock, Mail, User } from 'lucide-react';

const Auth: React.FC = () => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { loginUser } = useAuth();
  const navigate = useNavigate();

  // Demo credentials for testing
  const DEMO_EMAIL = 'admin@ddr-platform.com';
  const DEMO_PASSWORD = 'DDR@2024!Secure';
  const DEMO_NAME = 'John Doe';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Demo mode: accept demo credentials locally when API is unreachable
      if (email === DEMO_EMAIL && password === DEMO_PASSWORD) {
        loginUser('demo_token_ddr_platform_2024', { email: DEMO_EMAIL, name: DEMO_NAME });
        navigate('/');
        return;
      }

      if (mode === 'login') {
        const res = await login(email, password);
        loginUser(res.access_token, res.user);
      } else {
        const res = await register(email, password, name);
        loginUser(res.access_token, res.user);
      }
      navigate('/');
    } catch (err: any) {
      if (email === DEMO_EMAIL && password !== DEMO_PASSWORD) {
        setError('Invalid password for demo account.');
      } else {
        setError(err.message || 'Authentication failed. Use demo credentials or connect a backend.');
      }
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = () => {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    setMode('login');
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <span className="text-3xl mb-2 block">🛢️</span>
          <h1 className="text-2xl font-bold text-foreground">DDR Intelligence Platform</h1>
          <p className="text-sm text-muted-foreground mt-1">Saudi Aramco · OPERLMTDMRREP</p>
        </div>

        {/* Form */}
        <div className="card-surface p-6">
          <div className="flex gap-1 mb-6">
            <button
              onClick={() => { setMode('login'); setError(''); }}
              className={`flex-1 py-2 text-sm rounded transition-colors ${mode === 'login' ? 'bg-primary text-primary-foreground font-medium' : 'bg-muted text-muted-foreground'}`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setMode('register'); setError(''); }}
              className={`flex-1 py-2 text-sm rounded transition-colors ${mode === 'register' ? 'bg-primary text-primary-foreground font-medium' : 'bg-muted text-muted-foreground'}`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Full Name</label>
                <div className="flex items-center gap-2 card-surface px-3 py-2 rounded">
                  <User className="w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="John Doe"
                    className="bg-transparent text-sm text-foreground outline-none flex-1 placeholder:text-muted-foreground"
                    required
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Email</label>
              <div className="flex items-center gap-2 card-surface px-3 py-2 rounded">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@ddr-platform.com"
                  className="bg-transparent text-sm text-foreground outline-none flex-1 placeholder:text-muted-foreground"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Password</label>
              <div className="flex items-center gap-2 card-surface px-3 py-2 rounded">
                <Lock className="w-4 h-4 text-muted-foreground" />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="bg-transparent text-sm text-foreground outline-none flex-1 placeholder:text-muted-foreground"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/10 p-2 rounded">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-primary text-primary-foreground rounded font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 border-t border-border pt-4">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2 text-center">Demo Access</div>
            <button
              onClick={fillDemo}
              className="w-full py-2 text-xs card-surface border border-primary/30 text-primary rounded hover:bg-primary/10 transition-colors"
            >
              Use Demo Credentials
            </button>
            <div className="mt-2 text-[10px] text-muted-foreground text-center space-y-0.5">
              <div>Email: <span className="font-mono-data text-foreground">admin@ddr-platform.com</span></div>
              <div>Password: <span className="font-mono-data text-foreground">DDR@2024!Secure</span></div>
            </div>
          </div>
        </div>

        <div className="text-center mt-4 text-[10px] text-muted-foreground">
          SAUDI ARAMCO: CONFIDENTIAL — DDR Intelligence Platform v3.0
        </div>
      </div>
    </div>
  );
};

export default Auth;
