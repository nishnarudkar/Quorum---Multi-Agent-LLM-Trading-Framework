'use client';

import React, { useState } from 'react';
import { X, Loader2, ExternalLink } from 'lucide-react';

interface CheckoutModalProps {
    isOpen: boolean;
    onClose: () => void;
    initialTicker?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CheckoutModal({ isOpen, onClose, initialTicker = '' }: CheckoutModalProps) {
    const [ticker, setTicker] = useState(initialTicker);
    const [assetType, setAssetType] = useState<'stock' | 'crypto'>('stock');
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');

    if (!isOpen) return null;

    const handleCheckout = async () => {
        setIsProcessing(true);
        setError('');

        try {
            const res = await fetch(`${API_BASE}/locus/checkout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, asset_type: assetType }),
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Checkout failed');
            }

            const session = await res.json();
            
            if (!session.session_id) {
                throw new Error("No session ID returned from server");
            }

            // Store session ID for the report page to pick up
            localStorage.setItem('quorum_session_id', session.session_id);
            
            // Handle the checkout URL (might be relative for mock, or absolute for Locus)
            let finalUrl = session.checkout_url;
            if (finalUrl && finalUrl.startsWith('/')) {
                finalUrl = `${API_BASE}${finalUrl}`;
            }

            if (finalUrl) {
                if (session.mock) {
                    // For mock sessions, hit the endpoint in the background to simulate payment
                    await fetch(finalUrl).catch(console.error);
                } else {
                    // Open the Locus checkout URL in a new tab
                    window.open(finalUrl, '_blank');
                }
            } else {
                console.error("Missing checkout_url in session:", session);
            }
            
            // Redirect current page to the report status page
            window.location.href = `/report?session_id=${session.session_id}`;
            
        } catch (err: any) {
            setError(err.message);
            setIsProcessing(false);
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <div className="modal-header">
                    <h3>Locus Checkout</h3>
                    <button onClick={onClose} className="close-btn"><X size={18} /></button>
                </div>

                <div className="modal-body">
                    <p className="modal-desc">
                        Run a full institutional-grade analysis with 13 AI agents.
                        Report delivered in ~3 minutes.
                    </p>

                    <div className="form-group">
                        <label>Ticker / Token Symbol</label>
                        <input 
                            type="text" 
                            value={ticker} 
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                            placeholder="AAPL, NVDA, BTC/USD"
                            disabled={isProcessing}
                        />
                    </div>

                    <div className="form-group">
                        <label>Asset Class</label>
                        <div className="toggle-group">
                            <button 
                                className={assetType === 'stock' ? 'active' : ''} 
                                onClick={() => setAssetType('stock')}
                                disabled={isProcessing}
                            >
                                Stock
                            </button>
                            <button 
                                className={assetType === 'crypto' ? 'active' : ''} 
                                onClick={() => setAssetType('crypto')}
                                disabled={isProcessing}
                            >
                                Crypto
                            </button>
                        </div>
                    </div>

                    {error && <div className="error-box">{error}</div>}

                    <button 
                        className="checkout-btn" 
                        onClick={handleCheckout}
                        disabled={isProcessing || !ticker}
                    >
                        {isProcessing ? (
                            <>
                                <Loader2 className="animate-spin" size={18} />
                                PROCESSING...
                            </>
                        ) : (
                            <>
                                Get Analysis — $5 USDC
                                <ExternalLink size={16} />
                            </>
                        )}
                    </button>

                    <p className="modal-footer-text">
                        Powered by Base & Locus. Payments settle instantly.
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
                .checkout-btn {
                    width: 100%;
                    background: var(--bull);
                    color: #000;
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
                .checkout-btn:hover:not(:disabled) {
                    transform: translateY(-1px);
                    filter: brightness(1.1);
                }
                .checkout-btn:disabled {
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
