'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle2, AlertCircle, Terminal, ShieldCheck } from 'lucide-react';

interface LogEntry {
    agent: string;
    stage: string;
    message: string;
    details?: string;
    timestamp: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/live';

function ReportContent() {
    const searchParams = useSearchParams();
    const sessionId = searchParams.get('session_id');
    
    const [status, setStatus] = useState<'payment' | 'live' | 'completed' | 'error'>('payment');
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState('');
    
    const wsRef = useRef<WebSocket | null>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!sessionId) {
            setStatus('error');
            setError('No session ID provided');
            return;
        }

        let pollInterval: NodeJS.Timeout;

        const checkStatus = async () => {
            try {
                const res = await fetch(`${API_BASE}/locus/checkout/${sessionId}/status`);
                if (!res.ok) throw new Error('Failed to check status');
                const data = await res.json();

                if (data.paid) {
                    setStatus('live');
                    clearInterval(pollInterval);
                    connectWS();
                }
            } catch (err: any) {
                console.error('Polling error:', err);
            }
        };

        const connectWS = () => {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    // Match either session_id or analysis_id (some backends might use different keys)
                    if (msg.type === 'analysis_log' && (msg.session_id === sessionId || msg.analysis_id === sessionId)) {
                        setLogs(prev => [...prev, msg.data]);
                    }
                    if (msg.type === 'analysis_complete' && (msg.session_id === sessionId || msg.analysis_id === sessionId)) {
                        setResult(msg.data);
                        setStatus('completed');
                        ws.close();
                    }
                    if (msg.type === 'analysis_error' && (msg.session_id === sessionId || msg.analysis_id === sessionId)) {
                        setError(msg.data.error || 'Analysis failed');
                        setStatus('error');
                        ws.close();
                    }
                } catch (err) {
                    console.error('WS Message error:', err);
                }
            };

            ws.onclose = () => {
                if (status === 'live') {
                    setTimeout(connectWS, 3000);
                }
            };
        };

        pollInterval = setInterval(checkStatus, 3000);
        checkStatus();

        return () => {
            clearInterval(pollInterval);
            wsRef.current?.close();
        };
    }, [sessionId]);

    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    if (status === 'error') {
        return (
            <div className="report-container center">
                <AlertCircle size={48} color="var(--bear)" />
                <h2>Oops! Something went wrong.</h2>
                <p>{error}</p>
                <button onClick={() => window.location.href = '/dashboard'} className="btn mt-4">Back to Dashboard</button>
            </div>
        );
    }

    if (status === 'payment') {
        return (
            <div className="report-container center">
                <div className="spinner-box">
                    <Loader2 className="animate-spin" size={48} color="var(--accent)" />
                </div>
                <h2>Confirming Payment...</h2>
                <p>Waiting for USDC settlement on Base. This usually takes 5-10 seconds.</p>
                <div className="session-tag">SESSION: {sessionId?.slice(0, 8)}</div>
            </div>
        );
    }

    if (status === 'live') {
        return (
            <div className="report-container">
                <div className="report-header">
                    <div>
                        <h1>Analysis in Progress</h1>
                        <p>13 agents are currently debating your trade...</p>
                    </div>
                    <div className="live-badge">
                        <span className="pulse"></span> LIVE
                    </div>
                </div>

                <div className="terminal">
                    <div className="terminal-header">
                        <Terminal size={14} />
                        <span>AGENT_LOGS_STREAM</span>
                    </div>
                    <div className="terminal-body">
                        {logs.length === 0 && <div className="terminal-line muted">Initializing agents...</div>}
                        {logs.map((log, i) => (
                            <div key={i} className="terminal-line">
                                <span className="timestamp">[{log.timestamp.split('T')[1].split('.')[0]}]</span>
                                <span className="agent" style={{ color: 'var(--accent)' }}>{log.agent}</span>
                                <span className="message">{log.message}</span>
                            </div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                </div>
            </div>
        );
    }

    // Completed Phase
    return (
        <div className="report-container">
            <div className="report-header-success">
                <CheckCircle2 size={32} color="var(--bull)" />
                <div>
                    <h1>Analysis Complete</h1>
                    <p>{result?.ticker} · {result?.asset_type?.toUpperCase()} · Generated {new Date().toLocaleTimeString()}</p>
                </div>
            </div>

            <div className="report-grid">
                <div className="verdict-card">
                    <div className="card-label">JUDGE VERDICT</div>
                    <div className={`verdict-value ${result?.investment_debate?.judge_verdict?.toLowerCase().includes('bull') ? 'bull' : 'bear'}`}>
                        {result?.investment_debate?.judge_verdict?.toUpperCase() || 'NEUTRAL'}
                    </div>
                    <div className="confidence-section">
                        <div className="label-row">
                            <span>CONVICTION SCORE</span>
                            <span>{((result?.investment_debate?.judge_confidence || 0) * 10).toFixed(1)}/10</span>
                        </div>
                        <div className="bar-bg">
                            <div className="bar-fill" style={{ width: `${(result?.investment_debate?.judge_confidence || 0) * 100}%` }}></div>
                        </div>
                    </div>
                    {result?.trade_approved && (
                        <div className="risk-badge">
                            <ShieldCheck size={14} /> RISK COMMITTEE APPROVED
                        </div>
                    )}
                </div>

                <div className="thesis-card">
                    <div className="card-label">INVESTMENT THESIS</div>
                    <p>{result?.investment_debate?.investment_thesis}</p>
                </div>

                <div className="trade-card">
                    <div className="card-label">TRADE SIGNAL</div>
                    <div className="signal-grid">
                        <div className="signal-item">
                            <span className="label">ENTRY</span>
                            <span className="val">${result?.trade_signal?.entry_price || '0.00'}</span>
                        </div>
                        <div className="signal-item">
                            <span className="label">TARGET</span>
                            <span className="val bull">${result?.trade_signal?.target_price || '0.00'}</span>
                        </div>
                        <div className="signal-item">
                            <span className="label">STOP</span>
                            <span className="val bear">${result?.trade_signal?.stop_loss || '0.00'}</span>
                        </div>
                        <div className="signal-item">
                            <span className="label">SIZE</span>
                            <span className="val">{((result?.trade_signal?.position_size_pct || 0) * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>

                <div className="debate-card">
                    <div className="card-label">DEBATE SUMMARY</div>
                    <div className="debate-cols">
                        <div className="bull-col">
                            <h4>BULL CASE</h4>
                            <p>{result?.investment_debate?.bull_arguments?.[result.investment_debate.bull_arguments.length - 1]?.content || 'Bull thesis pending...'}</p>
                        </div>
                        <div className="bear-col">
                            <h4>BEAR CASE</h4>
                            <p>{result?.investment_debate?.bear_arguments?.[result.investment_debate.bear_arguments.length - 1]?.content || 'Bear thesis pending...'}</p>
                        </div>
                    </div>
                </div>
            </div>

            <style jsx>{`
                .report-container {
                    padding: 40px;
                    max-width: 1000px;
                    margin: 0 auto;
                    min-height: 80vh;
                }
                .report-container.center {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                }
                h1 { font-family: 'Space Grotesk', sans-serif; margin-bottom: 8px; }
                h2 { font-family: 'Space Grotesk', sans-serif; margin: 20px 0 10px; }
                p { color: var(--text-muted); }
                
                .session-tag {
                    margin-top: 24px;
                    font-size: 0.7rem;
                    font-family: 'JetBrains Mono', monospace;
                    padding: 4px 10px;
                    background: var(--bg-2);
                    border: 1px solid var(--line);
                    color: var(--text-muted);
                }

                .report-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 32px;
                }
                .live-badge {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: rgba(248, 113, 113, 0.1);
                    color: var(--bear);
                    padding: 6px 12px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem;
                    font-weight: 700;
                    border: 1px solid var(--bear);
                }
                .pulse {
                    width: 8px;
                    height: 8px;
                    background: var(--bear);
                    border-radius: 50%;
                    animation: pulse 1.5s infinite;
                }
                @keyframes pulse {
                    0% { opacity: 1; box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.7); }
                    70% { opacity: 0.5; box-shadow: 0 0 0 10px rgba(248, 113, 113, 0); }
                    100% { opacity: 1; box-shadow: 0 0 0 0 rgba(248, 113, 113, 0); }
                }

                .terminal {
                    background: #000;
                    border: 1px solid var(--line);
                    border-radius: 4px;
                    overflow: hidden;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                }
                .terminal-header {
                    background: var(--bg-2);
                    padding: 8px 16px;
                    border-bottom: 1px solid var(--line);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.7rem;
                    color: var(--text-muted);
                }
                .terminal-body {
                    padding: 20px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.85rem;
                    height: 400px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .terminal-line { display: flex; gap: 12px; line-height: 1.4; }
                .timestamp { color: #555; white-space: nowrap; }
                .agent { font-weight: 600; white-space: nowrap; min-width: 140px; }
                .message { color: #cfd3dc; }
                .muted { color: #444; }

                .report-header-success {
                    display: flex;
                    align-items: center;
                    gap: 20px;
                    margin-bottom: 40px;
                }

                .report-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 24px;
                }
                .card-label {
                    font-size: 0.7rem;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    margin-bottom: 12px;
                }
                .verdict-card, .thesis-card, .trade-card, .debate-card {
                    background: var(--bg-1);
                    border: 1px solid var(--line);
                    padding: 24px;
                }
                .verdict-value {
                    font-family: 'Space Grotesk', sans-serif;
                    font-size: 2.2rem;
                    font-weight: 700;
                    margin-bottom: 16px;
                }
                .verdict-value.bull { color: var(--bull); }
                .verdict-value.bear { color: var(--bear); }
                
                .confidence-section { margin-top: 20px; }
                .label-row { display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 8px; }
                .bar-bg { height: 8px; background: var(--bg-3); border-radius: 4px; overflow: hidden; }
                .bar-fill { height: 100%; background: var(--accent); }
                
                .risk-badge {
                    margin-top: 24px;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 0.7rem;
                    font-weight: 700;
                    color: var(--bull);
                    background: rgba(52, 211, 153, 0.1);
                    padding: 4px 10px;
                    border: 1px solid var(--bull);
                }

                .thesis-card { grid-column: 2; grid-row: 1 / 3; }
                .thesis-card p { font-size: 0.95rem; line-height: 1.7; color: #cfd3dc; }

                .trade-card { grid-column: 1; }
                .signal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
                .signal-item { display: flex; flex-direction: column; }
                .signal-item .label { font-size: 0.65rem; color: var(--text-muted); }
                .signal-item .val { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; font-weight: 600; }
                .val.bull { color: var(--bull); }
                .val.bear { color: var(--bear); }

                .debate-card { grid-column: 1 / 3; }
                .debate-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
                .debate-cols h4 { font-size: 0.75rem; letter-spacing: 0.05em; margin-bottom: 12px; }
                .bull-col h4 { color: var(--bull); }
                .bear-col h4 { color: var(--bear); }
                .debate-cols p { font-size: 0.85rem; line-height: 1.6; }

                @media (max-width: 768px) {
                    .report-grid { grid-template-columns: 1fr; }
                    .thesis-card { grid-column: 1; grid-row: auto; }
                    .debate-card { grid-column: 1; }
                    .debate-cols { grid-template-columns: 1fr; gap: 24px; }
                }
            `}</style>
        </div>
    );
}

export default function ReportPage() {
    return (
        <Suspense fallback={<div className="report-container center"><Loader2 className="animate-spin" size={48} /></div>}>
            <ReportContent />
        </Suspense>
    );
}
