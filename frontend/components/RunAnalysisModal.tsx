'use client';

import React, { useState } from 'react';
import { X, Loader2, ArrowRight } from 'lucide-react';

interface RunAnalysisModalProps {
    isOpen: boolean;
    onClose: () => void;
    initialTicker?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RunAnalysisModal({ isOpen, onClose, initialTicker = '' }: RunAnalysisModalProps) {
    const [ticker, setTicker] = useState(initialTicker);
    const [assetType, setAssetType] = useState<'stock' | 'crypto'>('stock');
    const [isStarting, setIsStarting] = useState(false);
    const [error, setError] = useState('');

    if (!isOpen) return null;

    const handleStart = async () => {
        setIsStarting(true);
        setError('');

        try {
            const res = await fetch(`${API_BASE}/analyses`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, asset_type: assetType }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to start analysis');
            }

            const job = await res.json();
            if (!job.analysis_id) {
                throw new Error('No analysis ID returned from server');
            }

            window.location.href = `/report?id=${job.analysis_id}`;
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to start analysis');
            setIsStarting(false);
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <div className="modal-header">
                    <h3>Run an analysis</h3>
                    <button onClick={onClose} className="close-btn" aria-label="Close"><X size={18} /></button>
                </div>

                <div className="modal-body">
                    <p className="modal-desc">
                        Twelve AI agents research, debate and risk-check the asset.
                        Watch the debate live; the full report takes a few minutes.
                    </p>

                    <div className="form-group">
                        <label htmlFor="ticker-input">Ticker / Token Symbol</label>
                        <input
                            id="ticker-input"
                            type="text"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                            onKeyDown={(e) => { if (e.key === 'Enter' && ticker && !isStarting) handleStart(); }}
                            placeholder="AAPL, NVDA, BTC/USD"
                            disabled={isStarting}
                            autoFocus
                        />
                    </div>

                    <div className="form-group">
                        <label>Asset Class</label>
                        <div className="toggle-group">
                            <button
                                className={assetType === 'stock' ? 'active' : ''}
                                onClick={() => setAssetType('stock')}
                                disabled={isStarting}
                            >
                                Stock
                            </button>
                            <button
                                className={assetType === 'crypto' ? 'active' : ''}
                                onClick={() => setAssetType('crypto')}
                                disabled={isStarting}
                            >
                                Crypto
                            </button>
                        </div>
                    </div>

                    {error && <div className="error-box">{error}</div>}

                    <button
                        className="start-btn"
                        onClick={handleStart}
                        disabled={isStarting || !ticker}
                    >
                        {isStarting ? (
                            <>
                                <Loader2 className="animate-spin" size={18} />
                                STARTING...
                            </>
                        ) : (
                            <>
                                Start analysis
                                <ArrowRight size={16} />
                            </>
                        )}
                    </button>

                    <p className="modal-footer-text">
                        Research only — not financial advice. Trades execute on Alpaca paper accounts.
                    </p>
                </div>
            </div>

            <style jsx>{`
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.85);
                    backdrop-filter: blur(4px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 16px;
                    z-index: 2000;
                }
                .modal-content {
                    width: 100%;
                    max-width: 420px;
                    background: var(--bg-1);
                    border: 1px solid var(--line);
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
                }
                .modal-header {
                    padding: 16px 20px;
                    border-bottom: 1px solid var(--line);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .modal-header h3 {
                    font-family: 'Space Grotesk', sans-serif;
                    font-size: 1.1rem;
                    margin: 0;
                }
                .close-btn {
                    background: none;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                }
                .modal-body {
                    padding: 24px;
                }
                .modal-desc {
                    font-size: 0.85rem;
                    color: var(--text-muted);
                    margin-bottom: 24px;
                    line-height: 1.5;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                .form-group label {
                    display: block;
                    font-size: 0.7rem;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    color: var(--text-muted);
                    margin-bottom: 8px;
                }
                input {
                    width: 100%;
                    background: var(--bg-2);
                    border: 1px solid var(--line);
                    padding: 12px;
                    color: var(--text);
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.95rem;
                }
                input:focus {
                    outline: none;
                    border-color: var(--accent);
                }
                .toggle-group {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    background: var(--bg-2);
                    padding: 4px;
                    border: 1px solid var(--line);
                }
                .toggle-group button {
                    background: none;
                    border: none;
                    padding: 8px;
                    color: var(--text-muted);
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.8rem;
                    cursor: pointer;
                }
                .toggle-group button.active {
                    background: var(--accent);
                    color: white;
                }
                .error-box {
                    background: rgba(248, 113, 113, 0.1);
                    border: 1px solid var(--bear);
                    color: var(--bear);
                    padding: 12px;
                    font-size: 0.8rem;
                    margin-bottom: 20px;
                    font-family: 'JetBrains Mono', monospace;
                }
                .start-btn {
                    width: 100%;
                    background: var(--accent);
                    color: #fff;
                    border: none;
                    padding: 16px;
                    font-family: 'JetBrains Mono', monospace;
                    font-weight: 700;
                    font-size: 0.9rem;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    transition: transform 0.1s;
                }
                .start-btn:hover:not(:disabled) {
                    transform: translateY(-1px);
                    filter: brightness(1.1);
                }
                .start-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .modal-footer-text {
                    font-size: 0.65rem;
                    color: var(--text-muted);
                    text-align: center;
                    margin-top: 16px;
                }
            `}</style>
        </div>
    );
}
