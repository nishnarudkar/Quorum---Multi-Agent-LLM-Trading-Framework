'use client';

import React, { useState, useEffect } from 'react';

interface PriceData {
    symbol: string;
    price: number;
    change_percent: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PriceTicker() {
    const [prices, setPrices] = useState<PriceData[]>([]);

    useEffect(() => {
        const fetchPrices = async () => {
            try {
                const res = await fetch(`${API_BASE}/realtime/prices`);
                if (res.ok) {
                    const data = await res.json();
                    setPrices(data);
                } else {
                    // Fallback to placeholders if API not ready
                    setPrices([
                        { symbol: 'BTC', price: 64231.50, change_percent: 2.4 },
                        { symbol: 'ETH', price: 3452.12, change_percent: -1.2 },
                        { symbol: 'SOL', price: 145.67, change_percent: 5.8 },
                        { symbol: 'AAPL', price: 189.45, change_percent: 0.8 },
                        { symbol: 'NVDA', price: 892.12, change_percent: 4.5 },
                    ]);
                }
            } catch (err) {
                console.error('Failed to fetch prices:', err);
            }
        };

        fetchPrices();
        const interval = setInterval(fetchPrices, 15000);
        return () => clearInterval(interval);
    }, []);

    if (prices.length === 0) return null;

    return (
        <div className="price-ticker-bar">
            <div className="price-ticker-scroll">
                {[...prices, ...prices].map((p, i) => (
                    <div key={i} className="price-item">
                        <span className="symbol">{p.symbol}</span>
                        <span className="price">${p.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        <span className={`change ${p.change_percent >= 0 ? 'up' : 'down'}`}>
                            {p.change_percent >= 0 ? '▲' : '▼'} {Math.abs(p.change_percent)}%
                        </span>
                    </div>
                ))}
            </div>
            <style jsx>{`
                .price-ticker-bar {
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 40px;
                    background: var(--bg-1);
                    border-top: 1px solid var(--line);
                    display: flex;
                    align-items: center;
                    overflow: hidden;
                    z-index: 1000;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.75rem;
                }
                .price-ticker-scroll {
                    display: flex;
                    white-space: nowrap;
                    animation: scroll 30s linear infinite;
                }
                .price-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 0 24px;
                    border-right: 1px solid var(--line);
                }
                .symbol {
                    color: var(--muted);
                    font-weight: 600;
                }
                .price {
                    color: var(--text);
                }
                .change.up {
                    color: var(--bull);
                }
                .change.down {
                    color: var(--bear);
                }
                @keyframes scroll {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
            `}</style>
        </div>
    );
}
