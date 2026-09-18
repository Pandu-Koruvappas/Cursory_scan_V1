import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { ShieldAlert, Activity, DollarSign, Database } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : 'https://ba-agent-aqd8c3d8dtdrbcat.centralus-01.azurewebsites.net'
);

const TelemetryDashboard = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false); // Simple admin check

  useEffect(() => {
    // In a real app, verify JWT role here
    setIsAdmin(true); 

    const fetchTelemetry = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/telemetry`);
        const result = await response.json();
        
        // Transform data for charts
        const formattedData = result.map(log => ({
          ...log,
          time: new Date(log.timestamp).toLocaleTimeString(),
          costCents: log.total_cost * 100 // Scale for better visibility
        })).reverse(); // Oldest to newest for Line Chart
        
        setData(formattedData);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch telemetry', error);
        setLoading(false);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 10000); // Auto-refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (!isAdmin) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <ShieldAlert className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold">Access Denied</h2>
          <p className="text-gray-400">Only Administrators can view LLMOps Telemetry.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Observability Engine</span>
          <h1>LLMOps Telemetry</h1>
          <p>Enterprise Agent Council Performance & Cost Analytics</p>
        </div>
      </header>

      {loading ? (
        <div className="loader-container">
          <div className="loader-ring"></div>
          <p>Loading Telemetry Streams...</p>
        </div>
      ) : (
        <div className="telemetry-content" style={{ marginTop: '24px' }}>
          
          {/* KPI Cards */}
          <div className="stat-tiles" style={{ marginBottom: '32px' }}>
            <div className="stat-tile glass-card">
              <div className="tile-top">
                <span className="tile-label">TOTAL CALLS</span>
                <span className="tile-trend"><Database size={16} /></span>
              </div>
              <div className="tile-main">
                <div className="tile-val">{data.length}</div>
                <div className="tile-label" style={{ fontSize: '0.6rem', opacity: 0.6 }}>Agent Invocations</div>
              </div>
            </div>
            
            <div className="stat-tile glass-card">
              <div className="tile-top">
                <span className="tile-label">AVG LATENCY</span>
                <span className="tile-trend"><Activity size={16} color="var(--success)" /></span>
              </div>
              <div className="tile-main">
                <div className="tile-val">
                  {data.length > 0 ? Math.round(data.reduce((a, b) => a + b.latency_ms, 0) / data.length) : 0} <span style={{fontSize:'1rem'}}>ms</span>
                </div>
                <div className="tile-label" style={{ fontSize: '0.6rem', opacity: 0.6 }}>Response Time</div>
              </div>
            </div>
            
            <div className="stat-tile glass-card">
              <div className="tile-top">
                <span className="tile-label">TOTAL COST</span>
                <span className="tile-trend"><DollarSign size={16} color="var(--warning)" /></span>
              </div>
              <div className="tile-main">
                <div className="tile-val">
                  ${data.reduce((a, b) => a + b.total_cost, 0).toFixed(4)}
                </div>
                <div className="tile-label" style={{ fontSize: '0.6rem', opacity: 0.6 }}>Estimated Tokens Cost</div>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '32px' }}>
            <div className="glass-card" style={{ padding: '24px', height: '400px' }}>
              <h3 style={{ marginBottom: '24px', fontSize: '1.1rem', color: 'var(--text-main)' }}>Latency over Time (ms)</h3>
              <ResponsiveContainer width="100%" height="85%">
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
                  <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis stroke="var(--text-muted)" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--secondary-bg)', border: '1px solid var(--glass-border)', borderRadius: '8px' }} />
                  <Legend />
                  <Line type="monotone" dataKey="latency_ms" stroke="var(--accent-primary)" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} name="Latency" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="glass-card" style={{ padding: '24px', height: '400px' }}>
              <h3 style={{ marginBottom: '24px', fontSize: '1.1rem', color: 'var(--text-main)' }}>Token Cost per Agent (Cents)</h3>
              <ResponsiveContainer width="100%" height="85%">
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
                  <XAxis dataKey="agent_name" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis stroke="var(--text-muted)" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--secondary-bg)', border: '1px solid var(--glass-border)', borderRadius: '8px' }} />
                  <Legend />
                  <Bar dataKey="costCents" fill="var(--warning)" radius={[4, 4, 0, 0]} name="Cost (Cents)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Data Grid */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <h3 style={{ marginBottom: '24px', fontSize: '1.1rem', color: 'var(--text-main)' }}>Recent Agent Invocations</h3>
            <table className="modern-table compact w-full">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Agent</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Latency (ms)</th>
                  <th>Tokens (P/C)</th>
                  <th>Cost</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.slice().reverse().map((log) => (
                  <tr key={log.id}>
                    <td className="mono-cell" style={{fontSize: '0.75rem'}}>{log.time}</td>
                    <td className="primary-cell">{log.agent_name}</td>
                    <td style={{textTransform: 'capitalize'}}>{log.provider}</td>
                    <td>{log.model_name}</td>
                    <td className="mono-cell">{Math.round(log.latency_ms)}</td>
                    <td className="mono-cell" style={{opacity: 0.7}}>{log.prompt_tokens} / {log.completion_tokens}</td>
                    <td className="mono-cell" style={{color: 'var(--warning)'}}>${log.total_cost.toFixed(4)}</td>
                    <td>
                      {log.success ? (
                        <span className="pill-badge completed">Success</span>
                      ) : (
                        <span className="pill-badge" style={{background: 'rgba(248, 81, 73, 0.2)', color: 'var(--error)', border: '1px solid rgba(248,81,73,0.5)'}} title={log.error_message}>
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default TelemetryDashboard;
