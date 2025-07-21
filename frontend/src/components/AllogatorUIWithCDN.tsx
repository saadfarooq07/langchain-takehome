import React, { useState, useEffect, useRef } from 'react';
import { analyzeLog } from '../services/api';

// This version uses Tailwind CDN - add this to index.html:
// <script src="https://cdn.tailwindcss.com"></script>

// --- SVG Icons ---
const AllogatorLogo = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M16.596 4.5H7.404L3 12l4.404 7.5h9.192L21 12l-4.404-7.5zM15.07 16.5H8.93l-3.536-6 3.536-6h6.14l3.536 6-3.536 6z" />
        <path d="M13.895 8.25h-3.79l-1.5 2.598 1.5 2.598h3.79l1.5-2.598-1.5-2.598z" />
    </svg>
);

const TerminalIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line>
  </svg>
);

const HistoryIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 4v6h6"></path><path d="M3.51 15a9 9 0 1 0 2.19-9.51L1 10"></path>
  </svg>
);

const AppsIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect>
    <rect x="3" y="14" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect>
  </svg>
);

const SettingsIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

export default function AllogatorUIWithCDN() {
    const [activeView, setActiveView] = useState('Dashboard');

    useEffect(() => {
        // Add Tailwind CDN if not already present
        if (!document.querySelector('script[src*="tailwindcss"]')) {
            const script = document.createElement('script');
            script.src = 'https://cdn.tailwindcss.com';
            document.head.appendChild(script);
        }
    }, []);

    return (
        <div className="flex h-screen bg-gray-950 font-sans">
            <div className="flex flex-col w-16 md:w-64 bg-gray-900 text-gray-200 border-r border-gray-800">
                <div className="flex items-center justify-center md:justify-start p-4 border-b border-gray-800 h-16">
                    <AllogatorLogo className="h-8 w-8 text-green-400" />
                    <span className="hidden md:inline ml-3 text-xl font-bold text-gray-100">Log Analyzer</span>
                </div>
                <nav className="flex-grow">
                    <button
                        onClick={() => setActiveView('Dashboard')}
                        className={`flex items-center w-full p-4 my-1 transition-colors duration-200 ${
                            activeView === 'Dashboard'
                                ? 'bg-green-900/30 border-l-4 border-green-400 text-white'
                                : 'hover:bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                    >
                        <TerminalIcon className="h-6 w-6" />
                        <span className="hidden md:inline mx-4 text-sm font-medium">Dashboard</span>
                    </button>
                </nav>
            </div>
            <main className="flex-1 h-full overflow-hidden bg-gray-950 p-6">
                <div className="bg-gray-800 rounded-lg p-4">
                    <h2 className="text-green-400 font-semibold mb-2">Log Analyzer Ready</h2>
                    <p className="text-gray-300">
                        The UI is working! You can now implement the full functionality.
                    </p>
                    <p className="text-gray-400 text-sm mt-2">
                        Using Tailwind CDN for styling.
                    </p>
                </div>
            </main>
        </div>
    );
}