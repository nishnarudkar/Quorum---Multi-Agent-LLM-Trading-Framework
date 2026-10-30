'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

const PriceTicker = dynamic(() => import('@/components/PriceTicker'), { ssr: false });
const RunAnalysisModal = dynamic(() => import('@/components/RunAnalysisModal'), { ssr: false });

export default function LandingPage() {
    const [isRunOpen, setIsRunOpen] = useState(false);
    useEffect(() => {
        const yearSpan = document.getElementById('y');
        if (yearSpan) yearSpan.textContent = new Date().getFullYear().toString();
    }, []);

    return (
        <div className="landing-container">
            <style jsx global>{`
                :root {
                    --bg: #0b0d12;
                    --bg-1: #10131a;
                    --bg-2: #161a23;
                    --bg-3: #1d222d;
                    --line: #262b38;
                    --text: #e6e8ec;
                    --muted: #8a909c;
                    --accent: #6c63ff;
                    --accent-dim: #6c63ff22;
                    --bull: #34d399;
                    --bear: #f87171;
                }

                .landing-container {
                    background: var(--bg);
                    color: var(--text);
                    font-family: 'JetBrains Mono', ui-monospace, monospace;
                    font-size: 15px;
                    line-height: 1.6;
                    -webkit-font-smoothing: antialiased;
                    background-image:
                        radial-gradient(circle at 15% 0%, #6c63ff14, transparent 40%),
                        radial-gradient(circle at 85% 30%, #6c63ff0a, transparent 50%);
                    min-height: 100vh;
                    position: relative;
                    z-index: 1;
                }

                .wrap { max-width: 1100px; margin: 0 auto; padding: 0 24px; }

                h1, h2, h3, h4 {
                    font-family: 'Space Grotesk', sans-serif;
                    font-weight: 600;
                    letter-spacing: -0.02em;
                    line-height: 1.1;
                }

                h1 { font-size: clamp(2.4rem, 5.2vw, 4.4rem); letter-spacing: -0.035em; }
                h2 { font-size: clamp(1.8rem, 3.4vw, 2.6rem); margin-bottom: .5rem; }
                h3 { font-size: 1.15rem; letter-spacing: -0.01em; }

                p { color: var(--muted); }

                header.nav {
                    position: sticky; top: 0; z-index: 50;
                    background: rgba(11, 13, 18, 0.78);
                    backdrop-filter: blur(12px);
                    border-bottom: 1px solid var(--line);
                }
                .nav-inner { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; max-width: 1100px; margin: 0 auto; }
                .logo { display: flex; align-items: center; gap: 10px; font-family: 'Space Grotesk'; font-weight: 700; font-size: 1.1rem; letter-spacing: -0.01em; }
                .logo-dot { width: 10px; height: 10px; background: var(--accent); box-shadow: 0 0 14px var(--accent); display: inline-block; }
                .nav-links { display: flex; gap: 28px; font-size: .85rem; color: var(--muted); }
                .nav-links a { color: inherit; text-decoration: none; }
                .nav-links a:hover { color: var(--text); }
                @media(max-width: 720px) { .nav-links { display: none; } }

                .btn {
                    display: inline-block;
                    background: var(--accent);
                    color: #fff;
                    padding: 14px 26px;
                    font-family: 'JetBrains Mono';
                    font-size: .9rem;
                    font-weight: 600;
                    letter-spacing: .02em;
                    border: 1px solid var(--accent);
                    box-shadow: 0 0 0 1px #6c63ff44, 0 0 30px #6c63ff44;
                    transition: transform .15s ease, box-shadow .15s ease;
                    cursor: pointer;
                    text-decoration: none;
                }
                .btn:hover { transform: translateY(-1px); box-shadow: 0 0 0 1px #6c63ff66, 0 0 40px #6c63ff66; }
                .btn-ghost { background: transparent; color: var(--text); border: 1px solid var(--line); box-shadow: none; }
                .btn-ghost:hover { border-color: var(--accent); box-shadow: none; }

                .hero { padding: 90px 0 60px; position: relative; }
                .eyebrow { display: inline-flex; align-items: center; gap: 8px; font-size: .78rem; color: var(--muted); border: 1px solid var(--line); padding: 6px 12px; margin-bottom: 28px; background: var(--bg-1); }
                .eyebrow .pulse { width: 6px; height: 6px; background: var(--bull); border-radius: 50%; box-shadow: 0 0 8px var(--bull); }
                .hero p.lead { font-size: clamp(1rem, 1.4vw, 1.15rem); max-width: 580px; margin-top: 22px; color: #b3b8c2; }
                .hero-cta { margin-top: 36px; display: flex; gap: 14px; flex-wrap: wrap; }
                .hero-meta { margin-top: 24px; font-size: .78rem; color: var(--muted); }

                .ticker {
                    margin-top: 64px;
                    border: 1px solid var(--line);
                    background: var(--bg-1);
                }
                .ticker-head {
                    display: flex; justify-content: space-between; align-items: center;
                    padding: 12px 18px; border-bottom: 1px solid var(--line);
                    font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .1em;
                }
                .ticker-head span:first-child::before { content: "●"; color: var(--bull); margin-right: 8px; animation: blink 1.4s infinite; }
                @keyframes blink { 50% { opacity: .3; } }
                .ticker-body { padding: 18px; display: grid; gap: 10px; font-size: .85rem; max-height: 280px; overflow: hidden; position: relative; }
                .ticker-body::after { content: ""; position: absolute; bottom: 0; left: 0; right: 0; height: 60px; background: linear-gradient(transparent, var(--bg-1)); }
                .log { display: grid; grid-template-columns: 80px 70px 1fr; gap: 14px; align-items: start; }
                .log .t { color: var(--muted); font-size: .72rem; padding-top: 2px; }
                .log .tag { font-size: .7rem; font-weight: 600; padding: 2px 6px; text-align: center; letter-spacing: .05em; }
                .tag-bull { background: #34d39915; color: var(--bull); border: 1px solid #34d39940; }
                .tag-bear { background: #f8717115; color: var(--bear); border: 1px solid #f8717140; }
                .tag-risk { background: #fbbf2415; color: #fbbf24; border: 1px solid #fbbf2440; }
                .tag-judge { background: var(--accent-dim); color: var(--accent); border: 1px solid #6c63ff60; }
                .log .msg { color: #cfd3dc; }

                section { padding: 88px 0; border-top: 1px solid var(--line); }
                .kicker { font-size: .78rem; color: var(--accent); text-transform: uppercase; letter-spacing: .15em; margin-bottom: 14px; }
                .sec-intro { max-width: 680px; margin-bottom: 48px; }
                .sec-intro p { margin-top: 10px; font-size: 1rem; }

                .problem-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--line); border: 1px solid var(--line); }
                .problem-grid > div { background: var(--bg); padding: 32px 26px; }
                .problem-grid h3 { margin-bottom: 10px; }
                .problem-grid .n { font-family: 'JetBrains Mono'; color: var(--muted); font-size: .78rem; margin-bottom: 14px; letter-spacing: .1em; }
                @media(max-width: 720px) { .problem-grid { grid-template-columns: 1fr; } }

                .pipeline { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
                .stage {
                    background: var(--bg-1);
                    border: 1px solid var(--line);
                    padding: 22px;
                    position: relative;
                }
                .stage.active { border-color: var(--accent); box-shadow: 0 0 0 1px #6c63ff44, inset 0 0 30px #6c63ff14; }
                .stage .step { font-size: .7rem; color: var(--muted); letter-spacing: .15em; margin-bottom: 14px; }
                .stage h3 { font-size: 1rem; margin-bottom: 8px; }
                .stage p { font-size: .82rem; line-height: 1.55; }
                .agents { margin-top: 14px; display: flex; flex-wrap: wrap; gap: 4px; }
                .agent { font-size: .65rem; padding: 2px 6px; background: var(--bg-3); color: #b3b8c2; border: 1px solid var(--line); }
                .agent.on { color: var(--accent); border-color: #6c63ff60; background: var(--accent-dim); }
                @media(max-width: 900px) { .pipeline { grid-template-columns: repeat(2, 1fr); } }
                @media(max-width: 520px) { .pipeline { grid-template-columns: 1fr; } }

                .report {
                    background: var(--bg-1);
                    border: 1px solid var(--line);
                    display: grid;
                    grid-template-columns: 1.1fr 1fr;
                }
                .report > div { padding: 28px; }
                .report-head { border-bottom: 1px solid var(--line); padding: 18px 28px !important; display: flex; justify-content: space-between; align-items: center; grid-column: 1/-1; }
                .report-head .tk { font-family: 'Space Grotesk'; font-size: 1.4rem; font-weight: 700; }
                .report-head .verdict { font-size: .75rem; letter-spacing: .1em; padding: 5px 10px; color: var(--bull); border: 1px solid #34d39940; background: #34d39912; }
                .tx-col { border-right: 1px solid var(--line); max-height: 380px; overflow: hidden; position: relative; }
                .tx-col::after { content: ""; position: absolute; bottom: 0; left: 0; right: 0; height: 80px; background: linear-gradient(transparent, var(--bg-1)); }
                .tx-col h4, .plan-col h4 { font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .12em; margin-bottom: 16px; }
                .tx { font-size: .78rem; margin-bottom: 14px; padding-left: 12px; border-left: 2px solid var(--line); }
                .tx.bull { border-left-color: var(--bull); }
                .tx.bear { border-left-color: var(--bear); }
                .tx.risk { border-left-color: #fbbf24; }
                .tx .who { font-size: .68rem; color: var(--muted); margin-bottom: 4px; letter-spacing: .08em; }
                .tx .body { color: #cfd3dc; line-height: 1.5; }
                .plan-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed var(--line); font-size: .85rem; }
                .plan-row span:first-child { color: var(--muted); }
                .plan-row .pos { color: var(--bull); }
                .plan-row .neg { color: var(--bear); }
                .catalysts { margin-top: 20px; font-size: .78rem; color: #cfd3dc; }
                .catalysts li { margin: 6px 0; padding-left: 18px; position: relative; list-style: none; }
                .catalysts li::before { content: "›"; position: absolute; left: 0; color: var(--accent); }
                @media(max-width: 780px) { .report { grid-template-columns: 1fr; } .tx-col { border-right: none; border-bottom: 1px solid var(--line); } }

                .price-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
                .price { background: var(--bg-1); border: 1px solid var(--line); padding: 32px; }
                .price.feature { border-color: var(--accent); box-shadow: 0 0 0 1px #6c63ff44, 0 0 60px #6c63ff15; }
                .price .tag-rec { display: inline-block; font-size: .7rem; color: var(--accent); letter-spacing: .1em; margin-bottom: 12px; }
                .price h3 { font-size: 1.3rem; }
                .price .per { color: var(--muted); font-size: .85rem; margin-top: 6px; }
                .price ul { list-style: none; margin: 22px 0; font-size: .85rem; }
                .price li { padding: 8px 0; color: #cfd3dc; border-bottom: 1px dashed var(--line); display: flex; gap: 10px; }
                .price li::before { content: "✓"; color: var(--accent); }
                @media(max-width: 720px) { .price-grid { grid-template-columns: 1fr; } }

                details { border: 1px solid var(--line); background: var(--bg-1); margin-bottom: 10px; padding: 18px 22px; }
                details[open] { border-color: #6c63ff60; }
                summary { cursor: pointer; font-family: 'Space Grotesk'; font-weight: 600; font-size: 1rem; list-style: none; display: flex; justify-content: space-between; align-items: center; }
                summary::-webkit-details-marker { display: none; }
                summary::after { content: "+"; color: var(--accent); font-size: 1.4rem; font-weight: 300; }
                details[open] summary::after { content: "−"; }
                details p { margin-top: 14px; font-size: .88rem; line-height: 1.65; }

                .final { text-align: center; padding: 100px 0; }
                .final h2 { font-size: clamp(2rem, 4vw, 3.2rem); max-width: 760px; margin: 0 auto 20px; }
                .final p { max-width: 520px; margin: 0 auto 32px; }

                footer { border-top: 1px solid var(--line); padding: 36px 0; font-size: .78rem; color: var(--muted); }
                footer a { color: var(--text); }
                .foot-inner { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; }

                @media (prefers-reduced-motion: no-preference) {
                    .hero h1, .hero p.lead, .hero-cta, .ticker { animation: fadeUp .8s ease both; }
                    .hero p.lead { animation-delay: .1s; }
                    .hero-cta { animation-delay: .2s; }
                    .ticker { animation-delay: .3s; }
                    @keyframes fadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
                }

                /* Override main content padding from AppShell */
                :global(.main-content) {
                    margin-left: 0 !important;
                    padding: 0 !important;
                    max-width: none !important;
                    min-height: 0 !important;
                }
                :global(.sidebar) {
                    display: none !important;
                }
            `}</style>

            <header className="nav">
                <div className="nav-inner">
                    <div className="logo"><span className="logo-dot"></span>QUORUM</div>
                    <nav className="nav-links">
                        <a href="#how">Pipeline</a>
                        <a href="#sample">Sample report</a>
                        <a href="#stack">Architecture</a>
                        <a href="#faq">FAQ</a>
                        <a href="/dashboard">Dashboard</a>
                        <a href="https://github.com/nishnarudkar/Quorum---Multi-Agent-LLM-Trading-Framework" target="_blank" rel="noopener noreferrer">GitHub</a>
                    </nav>
                    <button onClick={() => setIsRunOpen(true)} className="btn" style={{ padding: '10px 18px', fontSize: '.78rem' }}>Run analysis</button>
                </div>
            </header>

            <main>
                <section className="hero">
                    <div className="wrap">
                        <div className="eyebrow"><span className="pulse"></span> 12 AGENTS ONLINE · DEBATE ROOM OPEN</div>
                        <h1>Twelve AI agents will argue your next trade, before you make it.</h1>
                        <p className="lead">A multi-agent research desk built on LangGraph. Analysts gather the data, bull and bear researchers debate it, a risk committee pushes back, and every argument is streamed to you live.</p>
                        <div className="hero-cta">
                            <button onClick={() => setIsRunOpen(true)} className="btn">Run an analysis</button>
                            <a href="#sample" className="btn btn-ghost">See a sample</a>
                        </div>
                        <div className="hero-meta">Free &amp; open source · paper trading only · not financial advice</div>

                        <div className="ticker" aria-label="Live debate feed">
                            <div className="ticker-head">
                                <span>LIVE · NVDA / 03:42:11 UTC</span>
                                <span>DEBATE · ROUND 2 / 2</span>
                            </div>
                            <div className="ticker-body">
                                <div className="log"><span className="t">03:42:01</span><span className="tag tag-bull">BULL</span><span className="msg">Datacenter rev +154% YoY. Hyperscaler capex guides confirm orderbook through FY26. Mag-7 GPU TAM still expanding.</span></div>
                                <div className="log"><span className="t">03:42:04</span><span className="tag tag-bear">BEAR</span><span className="msg">Gross margin printed 75% — peak. China export controls now structural. Custom silicon at AMZN, GOOG accelerating.</span></div>
                                <div className="log"><span className="t">03:42:07</span><span className="tag tag-bull">BULL</span><span className="msg">CUDA moat ≠ silicon. Software switching cost compounding. Inference TAM dwarfs training; you&apos;re modeling the wrong cycle.</span></div>
                                <div className="log"><span className="t">03:42:09</span><span className="tag tag-risk">RISK</span><span className="msg">Position sizing must reflect 38% IV. Single-name exposure capped at 4% portfolio per committee charter.</span></div>
                                <div className="log"><span className="t">03:42:11</span><span className="tag tag-judge">JUDGE</span><span className="msg">Verdict pending. Bear case requires 2027 margin compression assumption Bull has not yet rebutted...</span></div>
                            </div>
                        </div>
                    </div>
                </section>

                <section id="problem">
                    <div className="wrap">
                        <div className="sec-intro">
                            <div className="kicker">The gap</div>
                            <h2>You have a full-time job. The market doesn&apos;t care.</h2>
                            <p>Most retail capital trades on Twitter screenshots and gut. Institutional desks don&apos;t. You shouldn&apos;t either.</p>
                        </div>
                        <div className="problem-grid">
                            <div>
                                <div className="n">01 / TIME</div>
                                <h3>A 10-K takes six hours</h3>
                                <p>Reading one filing is a Sunday. You manage twelve positions. The math doesn&apos;t work.</p>
                            </div>
                            <div>
                                <div className="n">02 / OPACITY</div>
                                <h3>Branded research is a black box</h3>
                                <p>Messari, Seeking Alpha, sell-side notes — you get a conclusion. You never see the argument that produced it.</p>
                            </div>
                            <div>
                                <div className="n">03 / CONVICTION</div>
                                <h3>One-sided takes destroy conviction</h3>
                                <p>If you can&apos;t articulate the bear case, you&apos;ll panic-sell at the bottom. Every time.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <section id="how">
                    <div className="wrap">
                        <div className="sec-intro">
                            <div className="kicker">The pipeline</div>
                            <h2>Twelve agents. One verdict. Full transcript.</h2>
                            <p>You don&apos;t trust the brand. You watch the work — every argument, dissent, and rebuttal is logged into your report.</p>
                        </div>
                        <div className="pipeline">
                            <div className="stage">
                                <div className="step">STAGE 01</div>
                                <h3>Intake & data</h3>
                                <p>Four analysts run in parallel over price action, technical indicators, news flow, sentiment, and fundamentals.</p>
                                <div className="agents"><span className="agent">MARKET</span><span className="agent">SENTIMENT</span><span className="agent">NEWS</span><span className="agent">FUNDAMENTALS</span></div>
                            </div>
                            <div className="stage active">
                                <div className="step">STAGE 02</div>
                                <h3>Adversarial debate</h3>
                                <p>A bull and a bear researcher argue over multiple rounds, each rebutting the prior turn. A research judge weighs the transcript.</p>
                                <div className="agents"><span className="agent on">BULL</span><span className="agent on">BEAR</span><span className="agent on">JUDGE</span></div>
                            </div>
                            <div className="stage">
                                <div className="step">STAGE 03</div>
                                <h3>Trader &amp; risk committee</h3>
                                <p>A trader drafts the plan; aggressive, conservative, and neutral risk analysts stress-test sizing, stops, and tail risk.</p>
                                <div className="agents"><span className="agent">TRADER</span><span className="agent">AGGRESSIVE</span><span className="agent">CONSERVATIVE</span><span className="agent">NEUTRAL</span></div>
                            </div>
                            <div className="stage">
                                <div className="step">STAGE 04</div>
                                <h3>Risk judge &amp; approval</h3>
                                <p>The chief risk officer signs off on the final plan. Low-confidence trades pause for your approval before any paper order is placed.</p>
                                <div className="agents"><span className="agent">CRO</span><span className="agent">YOU</span></div>
                            </div>
                        </div>
                    </div>
                </section>

                <section id="sample">
                    <div className="wrap">
                        <div className="sec-intro">
                            <div className="kicker">Glass-box output</div>
                            <h2>What you get, every report.</h2>
                            <p>The full transcript. Not a summary. Read every word the agents wrote — including the ones that lost the argument.</p>
                        </div>
                        <div className="report">
                            <div className="report-head">
                                <div>
                                    <div className="tk">NVDA · NASDAQ</div>
                                    <div style={{ fontSize: '.75rem', color: 'var(--muted)', marginTop: '4px' }}>Illustrative sample report</div>
                                </div>
                                <div className="verdict">VERDICT: LONG · CONVICTION 7.4 / 10</div>
                            </div>
                            <div className="tx-col">
                                <h4>Debate transcript (excerpt)</h4>
                                <div className="tx bull"><div className="who">BULL · ROUND 2</div><div className="body">&quot;Inference is now 40% of datacenter mix and growing. Bear&apos;s training-cycle peak thesis ignores that inference compute is consumed continuously, not in bursts.&quot;</div></div>
                                <div className="tx bear"><div className="who">BEAR · ROUND 2</div><div className="body">&quot;Concede inference durability. But Blackwell yield issues and the $4B ASP risk on H20 China-substitute SKUs are unmodeled in consensus. Q3 guide will surprise lower.&quot;</div></div>
                                <div className="tx bull"><div className="who">BULL · REBUTTAL</div><div className="body">&quot;H20 represents &lt;6% of next-quarter revenue at current run-rate. Even total impairment is sub-1% impact on FY EPS.&quot;</div></div>
                                <div className="tx risk"><div className="who">CONSERVATIVE · RISK COMMITTEE</div><div className="body">&quot;38% IV30, 1.7 beta. Position sizing capped at 4% NAV. Strike entry only on confirmed reclaim of 50DMA to avoid pre-earnings drift.&quot;</div></div>
                            </div>
                            <div className="plan-col">
                                <h4>Trade plan</h4>
                                <div className="plan-row"><span>Entry zone</span><span>$118.40 – $121.10</span></div>
                                <div className="plan-row"><span>Stop</span><span className="neg">$108.20 (−8.6%)</span></div>
                                <div className="plan-row"><span>Target 1</span><span className="pos">$142.00 (+18.7%)</span></div>
                                <div className="plan-row"><span>Target 2</span><span className="pos">$158.50 (+32.5%)</span></div>
                                <div className="plan-row"><span>Size</span><span>3.5% NAV max</span></div>
                                <div className="plan-row"><span>R:R</span><span>1 : 2.18</span></div>
                                <h4 style={{ marginTop: '24px' }}>Key catalysts</h4>
                                <ul className="catalysts">
                                    <li>Q3 earnings · Nov 19 — guidance on Blackwell yields</li>
                                    <li>GTC keynote · March — inference TAM update</li>
                                    <li>Hyperscaler capex prints (MSFT, META, GOOG)</li>
                                    <li>US export-control rule revisions on H20</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </section>

                <section id="stack">
                    <div className="wrap">
                        <div className="sec-intro">
                            <div className="kicker">Architecture</div>
                            <h2>How it&apos;s built.</h2>
                            <p>A stateful agent graph behind a streaming API, with a human checkpoint before anything trades.</p>
                        </div>
                        <div className="price-grid">
                            <div className="price">
                                <h3>Agent orchestration</h3>
                                <div className="per">LangGraph · Groq · ChromaDB</div>
                                <ul>
                                    <li>Parallel analyst fan-out with LangGraph Send</li>
                                    <li>Multi-round bull/bear and risk debates</li>
                                    <li>SQLite checkpointing; human-in-the-loop interrupts</li>
                                    <li>Vector memory of past decisions per agent</li>
                                    <li>API-key rotation and rate-limit backoff</li>
                                </ul>
                                <button onClick={() => setIsRunOpen(true)} className="btn" style={{ width: '100%', textAlign: 'center' }}>Run an analysis</button>
                            </div>
                            <div className="price feature">
                                <div className="tag-rec">▸ FULL STACK</div>
                                <h3>Data, streaming &amp; execution</h3>
                                <div className="per">FastAPI · WebSockets · Next.js</div>
                                <ul>
                                    <li>Yahoo Finance, Alpaca, and CCXT market data</li>
                                    <li>Live agent telemetry over WebSockets</li>
                                    <li>Background jobs with pollable results</li>
                                    <li>Alpaca paper-trade execution and P&amp;L tracking</li>
                                    <li>Watchlist scanner with Telegram/Discord alerts</li>
                                </ul>
                                <a href="/dashboard" className="btn" style={{ width: '100%', textAlign: 'center' }}>Open dashboard</a>
                            </div>
                        </div>
                    </div>
                </section>

                <section id="faq">
                    <div className="wrap">
                        <div className="sec-intro">
                            <div className="kicker">FAQ</div>
                            <h2>Reasonable questions.</h2>
                        </div>
                        <details><summary>How is this different from Messari, Seeking Alpha, or sell-side notes?</summary>
                            <p>Those are black boxes — you get a conclusion from an analyst whose incentives you can&apos;t see. Quorum is a glass box. You read every argument, every dissent, every rebuttal. If the bull case fails the rebuttal test, you watch it fail. The verdict is a byproduct of the transcript, not a brand statement.</p>
                        </details>
                        <details><summary>Is the output actually accurate? It&apos;s still AI.</summary>
                            <p>Agents work from real market data, indicators, news, and fundamentals, and the adversarial structure surfaces weak claims before they reach the verdict. Language models can still be wrong, which is exactly why the full transcript is published: audit the reasoning rather than trust a score. This is a research tool, not financial advice.</p>
                        </details>
                        <details><summary>What tickers and tokens are supported?</summary>
                            <p>US-listed equities and ETFs (via Yahoo Finance and Alpaca) and major crypto pairs such as BTC/USD and ETH/USD (via CCXT). Thinly traded assets may have incomplete data, which lowers agent confidence.</p>
                        </details>
                        <details><summary>Does it trade real money?</summary>
                            <p>No. Approved trades are sent to an Alpaca paper-trading account, and low-confidence signals wait for a human to approve or reject them first.</p>
                        </details>
                        <details><summary>Which models power the agents?</summary>
                            <p>Open-weight models served by Groq: a fast 20B model for the analysts, researchers, and debaters, and a 120B model for the judges that make the final calls. Models are configurable via environment variables.</p>
                        </details>
                    </div>
                </section>

                <section className="final">
                    <div className="wrap">
                        <h2>Pick a ticker. Let twelve agents fight it out.</h2>
                        <p>A few minutes, a full debate transcript, and a trade plan you can actually defend in a drawdown.</p>
                        <button onClick={() => setIsRunOpen(true)} className="btn">Run an analysis</button>
                    </div>
                </section>
            </main>

            <footer>
                <div className="wrap foot-inner">
                    <div className="logo"><span className="logo-dot"></span>QUORUM</div>
                    <div>Open-source multi-agent research · <a href="https://github.com/nishnarudkar/Quorum---Multi-Agent-LLM-Trading-Framework" target="_blank" rel="noopener noreferrer">GitHub</a> · © <span id="y">2025</span></div>
                    <div>Not financial advice. Markets are risky. Read the transcript.</div>
                </div>
            </footer>

            <PriceTicker />
            <RunAnalysisModal
                isOpen={isRunOpen}
                onClose={() => setIsRunOpen(false)}
            />
        </div>
    );
}
