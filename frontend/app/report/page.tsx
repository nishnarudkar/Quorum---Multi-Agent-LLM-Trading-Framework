'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle2, AlertCircle, Terminal, ShieldCheck, Activity, Cpu, Brain, Zap, TrendingUp, TrendingDown, Clock, Hash, Download } from 'lucide-react';
import dynamic from 'next/dynamic';

const PriceTicker = dynamic(() => import('@/components/PriceTicker'), { ssr: false });

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
    const [progress, setProgress] = useState(0);
    
    const wsRef = useRef<WebSocket | null>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);

    const handleDownloadPDF = () => {
        window.print();
    };

    // Calculate progress based on unique agents mentioned in logs
    useEffect(() => {
        const uniqueAgents = new Set(logs.map(l => l.agent)).size;
        // Total agents is 13
        const p = Math.min(Math.round((uniqueAgents / 13) * 100), 100);
        setProgress(p);
    }, [logs]);

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

                if (data.analysis_result) {
                    setResult(data.analysis_result);
                    setStatus('completed');
                    clearInterval(pollInterval);
                    return;
                }

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
            <div className="war-room error center">
                <AlertCircle size={64} color="var(--bear)" />
                <h1 className="mt-6">Pipeline Disrupted</h1>
                <p className="lead">{error}</p>
                <button onClick={() => window.location.href = '/'} className="btn mt-8">Return to Command Center</button>
                <style jsx>{styles}</style>
            </div>
        );
    }

    if (status === 'payment') {
        return (
            <div className="war-room center">
                <div className="hex-loader">
                    <div className="hex"></div>
                    <Loader2 className="animate-spin loader-icon" size={32} />
                </div>
                <h1 className="mt-8">Confirming Settlement</h1>
                <p className="lead">Verifying USDC transfer on Base network...</p>
                <div className="meta-badge">
                    <Hash size={12} />
                    <span>SESSION: {sessionId?.slice(0, 8)}</span>
                </div>
                <style jsx>{styles}</style>
            </div>
        );
    }

    if (status === 'live') {
        return (
            <div className="war-room">
                <div className="top-nav">
                    <div className="brand"><span className="dot"></span>QUORUM / DEBATE_ROOM</div>
                    <div className="session-info">
                        <div className="info-item"><Clock size={12} /> <span>{new Date().toLocaleTimeString()} UTC</span></div>
                        <div className="info-item"><Hash size={12} /> <span>{sessionId?.slice(0, 8)}</span></div>
                    </div>
                </div>

                <div className="main-layout">
                    {/* Left: Terminal Log */}
                    <div className="pane log-pane">
                        <div className="pane-header">
                            <div className="title"><Terminal size={14} /> <span>AGENT_DEBATE_TRANSCRIPT</span></div>
                            <div className="status-badge live"><span className="pulse"></span> LIVE_STREAM</div>
                        </div>
                        <div className="terminal-view">
                            {logs.length === 0 && (
                                <div className="init-msg">
                                    <Cpu className="animate-pulse" />
                                    <p>Initializing 13-agent consensus engine...</p>
                                </div>
                            )}
                            {logs.map((log, i) => (
                                <div key={i} className="log-line">
                                    <span className="ts">{log.timestamp?.split('T')[1]?.split('.')[0] || '00:00:00'}</span>
                                    <span className="ag">[{log.agent?.toUpperCase()}]</span>
                                    <span className="msg">{log.message}</span>
                                </div>
                            ))}
                            <div ref={logsEndRef} />
                        </div>
                    </div>

                    {/* Right: Status & Stats */}
                    <div className="pane stats-pane">
                        <div className="pane-header">
                            <div className="title"><Activity size={14} /> <span>ANALYSIS_TELEMETRY</span></div>
                        </div>
                        <div className="stats-content">
                            <div className="stat-card progress-card">
                                <div className="label-row">
                                    <span>CONSENSUS PROGRESS</span>
                                    <span>{progress}%</span>
                                </div>
                                <div className="p-bar-bg">
                                    <div className="p-bar-fill" style={{ width: `${progress}%` }}></div>
                                </div>
                                <div className="sub-label">{Math.floor(progress/7.7)} of 13 Agents Complete</div>
                            </div>

                            <div className="gauge-grid">
                                <div className="gauge-box">
                                    <div className="g-label">MARKET_VOL</div>
                                    <div className="g-val">NOMINAL</div>
                                    <div className="g-track"><div className="g-fill" style={{ width: '40%' }}></div></div>
                                </div>
                                <div className="gauge-box">
                                    <div className="g-label">SENTIMENT_HEAT</div>
                                    <div className="g-val">HIGH</div>
                                    <div className="g-track"><div className="g-fill danger" style={{ width: '85%' }}></div></div>
                                </div>
                            </div>

                            <div className="active-agents">
                                <h3>ACTIVE_PROCESSORS</h3>
                                <div className="agent-list">
                                    {['MARKET', 'NEWS', 'FUNDAMENTAL', 'MACRO', 'BULL_1', 'BEAR_1', 'JUDGE'].map(a => (
                                        <div key={a} className={`agent-chip ${logs.some(l => l.agent?.includes(a)) ? 'done' : 'waiting'}`}>
                                            {logs.some(l => l.agent?.includes(a)) ? <CheckCircle2 size={10} /> : <Zap size={10} />}
                                            {a}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="warning-box">
                                <AlertCircle size={14} />
                                <span>Adversarial debate active. Agents are cross-examining data sources for discrepancies.</span>
                            </div>
                        </div>
                    </div>
                </div>

                <PriceTicker />
                <style jsx>{styles}</style>
            </div>
        );
    }

    // Completed State
    return (
        <div className="war-room report-view">
            <div className="top-nav no-print">
                <div className="brand"><span className="dot"></span>QUORUM / FINAL_REPORT</div>
                <div className="nav-right">
                    <button className="btn-icon-text download-btn" onClick={handleDownloadPDF}>
                        <Download size={16} />
                        <span>DOWNLOAD_PDF</span>
                    </button>
                    <div className="verdict-tag">
                        VERDICT: <span className={result?.investment_debate?.judge_verdict?.toLowerCase().includes('bull') ? 'bull' : 'bear'}>
                            {result?.investment_debate?.judge_verdict?.toUpperCase() || 'NEUTRAL'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Print-only Header */}
            <div className="print-only-header">
                <div className="brand"><span className="dot"></span>QUORUM / INVESTMENT_REPORT</div>
                <div className="print-date">Generated on: {new Date().toLocaleDateString()} · Session: {sessionId?.slice(0, 8)}</div>
            </div>

            <div className="report-main">
                <header className="report-hero">
                    <div className="ticker-info">
                        <div className="t-main">{result?.ticker}</div>
                        <div className="t-sub">{result?.asset_type?.toUpperCase()} · NASDAQ LISTED</div>
                    </div>
                    <div className="score-box">
                        <div className="s-label">CONVICTION_SCORE</div>
                        <div className="s-val">{((result?.investment_debate?.judge_confidence || 0) * 10).toFixed(1)}<span>/10</span></div>
                    </div>
                </header>

                <div className="report-grid">
                    <div className="grid-left">
                        <section className="card thesis">
                            <h3><Brain size={16} /> EXECUTIVE_SUMMARY</h3>
                            <p>{result?.investment_debate?.investment_thesis}</p>
                            {result?.trade_approved && (
                                <div className="approved-badge">
                                    <ShieldCheck size={16} />
                                    <span>RISK_COMMITTEE_CERTIFIED</span>
                                </div>
                            )}
                        </section>

                        <section className="card signals">
                            <h3><Zap size={16} /> EXECUTION_PLAN</h3>
                            <div className="sig-row">
                                <div className="sig">
                                    <span className="l">ENTRY</span>
                                    <span className="v">${result?.trade_signal?.entry_price || '0.00'}</span>
                                </div>
                                <div className="sig">
                                    <span className="l">TARGET</span>
                                    <span className="v bull">${result?.trade_signal?.target_price || '0.00'}</span>
                                </div>
                                <div className="sig">
                                    <span className="l">STOP</span>
                                    <span className="v bear">${result?.trade_signal?.stop_loss || '0.00'}</span>
                                </div>
                                <div className="sig">
                                    <span className="l">NAV_ALLOC</span>
                                    <span className="v">{((result?.trade_signal?.position_size_pct || 0) * 100).toFixed(1)}%</span>
                                </div>
                            </div>
                        </section>
                    </div>

                    <div className="grid-right">
                        <section className="card debate">
                            <h3><Activity size={16} /> ADVERSARIAL_DEBATE_SUMMARY</h3>
                            <div className="debate-box">
                                <div className="case bull-case">
                                    <div className="c-head"><TrendingUp size={14} /> BULL_PRIMARY</div>
                                    <p>{result?.investment_debate?.bull_arguments?.[result.investment_debate.bull_arguments.length - 1]?.content || 'Thesis conceded...'}</p>
                                </div>
                                <div className="case bear-case">
                                    <div className="c-head"><TrendingDown size={14} /> BEAR_REBUTTAL</div>
                                    <p>{result?.investment_debate?.bear_arguments?.[result.investment_debate.bear_arguments.length - 1]?.content || 'Thesis conceded...'}</p>
                                </div>
                            </div>
                        </section>
                    </div>
                </div>
            </div>

            <PriceTicker />
            <style jsx>{styles}</style>
        </div>
    );
}

const styles = `
    .war-room {
        background: #0b0d12;
        color: #e6e8ec;
        min-height: 100vh;
        font-family: 'JetBrains Mono', monospace;
        position: relative;
        padding-bottom: 60px;
    }
    .war-room.center {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 40px;
    }
    .lead { color: #8a909c; font-size: 1.1rem; margin-top: 12px; max-width: 500px; }
    
    .hex-loader { position: relative; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; }
    .hex { 
        position: absolute; width: 100%; height: 100%; border: 2px solid #6c63ff22; 
        clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%); 
        animation: spin 4s linear infinite;
    }
    .loader-icon { color: #6c63ff; }
    
    .meta-badge {
        margin-top: 24px; display: flex; align-items: center; gap: 8px;
        background: #161a23; border: 1px solid #262b38; padding: 6px 12px;
        font-size: 0.7rem; color: #8a909c; border-radius: 4px;
    }

    .top-nav {
        display: flex; justify-content: space-between; align-items: center;
        padding: 20px 40px; border-bottom: 1px solid #262b38; background: #0b0d12;
    }
    .nav-right { display: flex; align-items: center; gap: 24px; }
    .download-btn {
        display: flex; align-items: center; gap: 8px;
        background: #6c63ff15; border: 1px solid #6c63ff40; color: #6c63ff;
        padding: 8px 16px; font-size: 0.7rem; font-weight: 800; cursor: pointer;
        transition: all 0.2s; border-radius: 4px;
    }
    .download-btn:hover { background: #6c63ff25; transform: translateY(-1px); }
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 0.9rem; letter-spacing: 0.05em; }
    .brand .dot { width: 8px; height: 8px; background: #6c63ff; box-shadow: 0 0 10px #6c63ff; }
    .session-info { display: flex; gap: 24px; font-size: 0.7rem; color: #8a909c; }
    .info-item { display: flex; align-items: center; gap: 6px; }

    .main-layout {
        display: grid; grid-template-columns: 1fr 380px; gap: 1px;
        background: #262b38; height: calc(100vh - 140px);
    }
    .pane { background: #0b0d12; display: flex; flex-direction: column; overflow: hidden; }
    .pane-header {
        padding: 14px 24px; border-bottom: 1px solid #262b38;
        display: flex; justify-content: space-between; align-items: center;
    }
    .pane-header .title { display: flex; align-items: center; gap: 10px; font-size: 0.75rem; font-weight: 700; color: #8a909c; }
    .status-badge { font-size: 0.65rem; font-weight: 800; padding: 4px 8px; background: #f8717115; color: #f87171; border: 1px solid #f8717140; }
    .pulse { display: inline-block; width: 6px; height: 6px; background: #f87171; border-radius: 50%; margin-right: 6px; animation: blink 1s infinite; }
    
    .terminal-view {
        flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;
        background: radial-gradient(circle at top right, #6c63ff05, transparent);
    }
    .init-msg { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #444; gap: 16px; }
    .log-line { display: grid; grid-template-columns: 80px 140px 1fr; gap: 16px; font-size: 0.8rem; line-height: 1.5; }
    .log-line .ts { color: #444; }
    .log-line .ag { color: #6c63ff; font-weight: 700; }
    .log-line .msg { color: #cfd3dc; }

    .stats-pane { background: #10131a; }
    .stats-content { padding: 32px; display: flex; flex-direction: column; gap: 32px; }
    
    .progress-card .label-row { display: flex; justify-content: space-between; font-size: 0.75rem; font-weight: 700; margin-bottom: 10px; }
    .p-bar-bg { height: 6px; background: #262b38; border-radius: 3px; overflow: hidden; }
    .p-bar-fill { height: 100%; background: #6c63ff; box-shadow: 0 0 15px #6c63ff; transition: width 0.5s ease; }
    .sub-label { font-size: 0.65rem; color: #8a909c; margin-top: 8px; }

    .gauge-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .gauge-box { background: #161a23; padding: 16px; border: 1px solid #262b38; border-radius: 4px; }
    .g-label { font-size: 0.6rem; color: #8a909c; margin-bottom: 6px; }
    .g-val { font-size: 0.9rem; font-weight: 800; margin-bottom: 10px; }
    .g-track { height: 3px; background: #262b38; }
    .g-fill { height: 100%; background: #34d399; width: 40%; }
    .g-fill.danger { background: #f87171; }

    .active-agents h3 { font-size: 0.7rem; color: #8a909c; margin-bottom: 16px; }
    .agent-list { display: flex; flex-wrap: wrap; gap: 8px; }
    .agent-chip { 
        display: flex; align-items: center; gap: 6px; font-size: 0.65rem; 
        padding: 6px 10px; border-radius: 4px; border: 1px solid #262b38;
    }
    .agent-chip.done { background: #34d39910; border-color: #34d39940; color: #34d399; }
    .agent-chip.waiting { background: #161a23; color: #444; }

    .warning-box {
        display: flex; gap: 12px; padding: 16px; background: #fbbf2408; 
        border: 1px solid #fbbf2430; border-radius: 4px; font-size: 0.7rem; color: #fbbf24bb;
    }

    /* Report Specific Styles */
    .report-view .report-main { padding: 40px; max-width: 1200px; margin: 0 auto; }
    .report-hero { display: flex; justify-content: space-between; align-items: center; margin-bottom: 48px; }
    .t-main { font-family: 'Space Grotesk'; font-size: 4rem; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
    .t-sub { color: #8a909c; font-size: 0.9rem; margin-top: 8px; letter-spacing: 0.1em; }
    
    .score-box { text-align: right; }
    .s-label { font-size: 0.7rem; color: #8a909c; margin-bottom: 8px; }
    .s-val { font-size: 3.5rem; font-weight: 800; font-family: 'Space Grotesk'; color: #6c63ff; line-height: 1; }
    .s-val span { font-size: 1.2rem; color: #444; }

    .report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
    .card { background: #10131a; border: 1px solid #262b38; padding: 32px; border-radius: 8px; }
    .card h3 { display: flex; align-items: center; gap: 12px; font-size: 0.8rem; color: #8a909c; margin-bottom: 24px; }
    
    .thesis p { font-size: 1.05rem; line-height: 1.75; color: #cfd3dc; }
    .approved-badge { 
        margin-top: 32px; display: inline-flex; align-items: center; gap: 10px;
        background: #34d39910; border: 1px solid #34d39940; color: #34d399;
        padding: 8px 16px; font-size: 0.75rem; font-weight: 700;
    }

    .sig-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
    .sig { display: flex; flex-direction: column; gap: 4px; }
    .sig .l { font-size: 0.65rem; color: #8a909c; }
    .sig .v { font-size: 1.5rem; font-weight: 700; }
    .sig .v.bull { color: #34d399; }
    .sig .v.bear { color: #f87171; }

    .debate-box { display: flex; flex-direction: column; gap: 32px; }
    .case { padding-left: 20px; border-left: 2px solid #262b38; }
    .case.bull-case { border-left-color: #34d399; }
    .case.bear-case { border-left-color: #f87171; }
    .c-head { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; font-weight: 700; margin-bottom: 12px; }
    .bull-case .c-head { color: #34d399; }
    .bear-case .c-head { color: #f87171; }
    .case p { font-size: 0.9rem; line-height: 1.6; color: #cfd3dc; }

    .verdict-tag { font-size: 0.85rem; font-weight: 800; }
    .bull { color: #34d399; }
    .bear { color: #f87171; }

    @keyframes blink { 50% { opacity: 0; } }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    @media (max-width: 1000px) {
        .main-layout { grid-template-columns: 1fr; height: auto; }
        .report-grid { grid-template-columns: 1fr; }
        .stats-pane { border-top: 1px solid #262b38; }
    }

    /* Print Styles */
    .print-only-header { display: none; }
    @media print {
        @page { size: A4; margin: 20mm; }
        .no-print { display: none !important; }
        .print-only-header { 
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #262b38;
        }
        .war-room { background: white !important; color: black !important; padding: 0 !important; }
        .report-view .report-main { padding: 0 !important; max-width: 100% !important; }
        .t-main { color: black !important; }
        .t-sub { color: #555 !important; }
        .s-val { color: #6c63ff !important; }
        .card { background: #f8f9fa !important; border: 1px solid #dee2e6 !important; color: black !important; break-inside: avoid; }
        .card h3 { color: #555 !important; }
        .thesis p, .case p { color: #222 !important; }
        .sig .l, .c-head { color: #555 !important; }
        .sig .v { color: black !important; }
        .bull { color: #059669 !important; }
        .bear { color: #dc2626 !important; }
        .approved-badge { background: #ecfdf5 !important; border-color: #10b981 !important; color: #059669 !important; }
        .report-grid { gap: 20px !important; }
        PriceTicker { display: none !important; }
    }
`;

export default function ReportPage() {
    return (
        <Suspense fallback={<div className="war-room center"><Loader2 className="animate-spin loader-icon" size={48} /></div>}>
            <ReportContent />
        </Suspense>
    );
}
