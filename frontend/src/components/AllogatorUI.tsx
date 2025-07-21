import React, { useState, useEffect, useRef } from 'react';
import { analyzeLog, analyzeLogStream, authService, analysisService } from '../services/api';
import DOMPurify from 'dompurify';

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

const UploadIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
    <polyline points="17 8 12 3 7 8"></polyline>
    <line x1="12" y1="3" x2="12" y2="15"></line>
  </svg>
);

const SparklesIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3L14.5 8.5L20 11L14.5 13.5L12 19L9.5 13.5L4 11L9.5 8.5L12 3Z" />
        <path d="M5 3L6 5L8 6L6 7L5 9L4 7L2 6L4 5L5 3Z" />
        <path d="M19 15L20 17L22 18L20 19L19 21L18 19L16 18L18 17L19 15Z" />
    </svg>
);

const ArrowRightIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
    </svg>
);

const CheckIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
);

// --- Components ---

const Sidebar = ({ activeView, setActiveView, isGuest }: { activeView: string; setActiveView: (view: string) => void; isGuest: boolean }) => {
    const navItems = [
        { name: 'Dashboard', icon: TerminalIcon },
        { name: 'History', icon: HistoryIcon },
        { name: 'Applications', icon: AppsIcon },
        { name: 'Settings', icon: SettingsIcon },
    ];

    const handleLogout = async () => {
        if (window.confirm('Are you sure you want to log out?')) {
            await authService.logout();
        }
    };

    // Get user info from localStorage
    const userStr = localStorage.getItem('allogator_user');
    const user = userStr ? JSON.parse(userStr) : null;

    return (
        <div className="flex flex-col w-16 md:w-64 bg-gray-900 text-gray-200 border-r border-gray-800">
            <div className="flex items-center justify-center md:justify-start p-4 border-b border-gray-800 h-16">
                <AllogatorLogo className="h-8 w-8 text-green-400" />
                <span className="hidden md:inline ml-3 text-xl font-bold text-gray-100">Log Analyzer</span>
            </div>
            <nav className="flex-grow">
                {navItems.map(item => (
                    <button
                        key={item.name}
                        onClick={() => setActiveView(item.name)}
                        className={`flex items-center w-full p-4 my-1 transition-colors duration-200 ${
                            activeView === item.name
                                ? 'bg-green-900/30 border-l-4 border-green-400 text-white'
                                : 'hover:bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                    >
                        <item.icon className="h-6 w-6" />
                        <span className="hidden md:inline mx-4 text-sm font-medium">{item.name}</span>
                    </button>
                ))}
            </nav>
            <div className="p-4 border-t border-gray-800">
                {isGuest ? (
                    <a 
                        href="/signup"
                        className="flex items-center justify-center w-full py-2 px-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                    >
                        <span className="hidden md:inline">Sign Up Free</span>
                        <span className="md:hidden">Sign Up</span>
                    </a>
                ) : (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center font-bold text-gray-900">
                                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
                            </div>
                            <div className="hidden md:block ml-3">
                                <p className="text-sm font-semibold text-white">{user?.full_name || user?.email || 'User'}</p>
                                <span className="text-xs text-green-400">{user?.tenant?.name || 'READY'}</span>
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="hidden md:block text-gray-400 hover:text-white transition-colors text-sm"
                            title="Logout"
                        >
                            <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                <polyline points="16 17 21 12 16 7"></polyline>
                                <line x1="21" y1="12" x2="9" y2="12"></line>
                            </svg>
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

interface AnalysisMessage {
    type: 'user' | 'agent';
    text: string;
    analysis?: any;
}

interface AnalysisHistory {
    id: string;
    query: string;
    date: string;
    issues: number;
    severity: string;
    analysis?: any;
}

const Dashboard = ({ isGuest, guestAnalysisCount, setGuestAnalysisCount, onUpgradePrompt, history, setHistory, fetchAnalysisHistory }: {
    isGuest: boolean;
    guestAnalysisCount: number;
    setGuestAnalysisCount: (count: number) => void;
    onUpgradePrompt: () => void;
    history: AnalysisHistory[];
    setHistory: (history: AnalysisHistory[]) => void;
    fetchAnalysisHistory: () => void;
}) => {
    const [input, setInput] = useState('');
    const [output, setOutput] = useState<AnalysisMessage[]>([
      { 
        type: 'agent', 
        text: isGuest && guestAnalysisCount === 0 
          ? '👋 Welcome to Allogator Beta! You have 5 free analyses - paste your logs below to see instant AI-powered analysis. No signup required!' 
          : isGuest 
          ? `Log Analyzer is ready. You have ${5 - guestAnalysisCount} free analyses remaining.` 
          : 'Log Analyzer is ready. Paste your logs or upload a file to begin analysis.' 
      },
    ]);
    const [isProcessing, setIsProcessing] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const outputEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        outputEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [output]);

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const content = e.target?.result as string;
                setInput(content);
            };
            reader.readAsText(file);
        }
    };

    const formatAnalysisResult = (result: any) => {
        let html = '<div class="space-y-4">';
        
        // Executive Summary
        if (result.executive_summary) {
            html += '<div class="bg-gray-800 rounded-lg p-4">';
            html += '<h3 class="text-green-400 font-semibold mb-2">Executive Summary</h3>';
            html += `<p class="text-gray-300">${DOMPurify.sanitize(result.executive_summary.overview || result.executive_summary || 'Analysis complete.')}</p>`;
            if (result.executive_summary.critical_issues?.length > 0) {
                html += '<div class="mt-2"><span class="text-red-400 font-semibold">Critical Issues:</span><ul class="list-disc list-inside mt-1">';
                result.executive_summary.critical_issues.forEach((issue: string) => {
                    html += `<li class="text-gray-300">${DOMPurify.sanitize(issue)}</li>`;
                });
                html += '</ul></div>';
            }
            html += '</div>';
        }
        
        // Issues
        if (result.issues && result.issues.length > 0) {
            html += '<div class="bg-gray-800 rounded-lg p-4">';
            html += '<h3 class="text-green-400 font-semibold mb-2">Issues Found</h3>';
            result.issues.forEach((issue: any, idx: number) => {
                const severityColor = {
                    critical: 'text-red-500',
                    high: 'text-orange-500',
                    medium: 'text-yellow-500',
                    low: 'text-blue-500'
                }[issue.severity] || 'text-gray-400';
                
                html += `<div class="mb-3 pb-3 ${idx < result.issues.length - 1 ? 'border-b border-gray-700' : ''}">`;
                html += `<div class="flex items-center gap-2 mb-1">`;
                html += `<span class="${severityColor} font-semibold">${issue.severity?.toUpperCase() || 'INFO'}</span>`;
                if (issue.type && issue.type !== 'general' && issue.type !== 'undefined') {
                    html += `<span class="text-gray-400">|</span>`;
                    html += `<span class="text-gray-300">${DOMPurify.sanitize(issue.type)}</span>`;
                }
                html += `</div>`;
                html += `<p class="text-gray-300">${DOMPurify.sanitize(issue.description)}</p>`;
                if (issue.root_cause) {
                    html += `<p class="text-sm text-gray-400 mt-1"><strong>Root Cause:</strong> ${DOMPurify.sanitize(issue.root_cause)}</p>`;
                }
                html += '</div>';
            });
            html += '</div>';
        }
        
        // Explanations
        if (result.explanations && result.explanations.length > 0) {
            html += '<div class="bg-gray-800 rounded-lg p-4">';
            html += '<h3 class="text-green-400 font-semibold mb-2">Explanations</h3>';
            html += '<div class="space-y-2">';
            result.explanations.forEach((exp: any) => {
                if (typeof exp === 'object' && exp.issue && exp.explanation) {
                    html += `<div class="mb-2">`;
                    html += `<p class="text-gray-400 font-semibold">${exp.issue}</p>`;
                    html += `<p class="text-gray-300 text-sm mt-1">${exp.explanation}</p>`;
                    html += `</div>`;
                } else if (typeof exp === 'string') {
                    html += `<p class="text-gray-300">${exp}</p>`;
                }
            });
            html += '</div>';
            html += '</div>';
        }
        
        // Recommendations
        if (result.suggestions && result.suggestions.length > 0) {
            html += '<div class="bg-gray-800 rounded-lg p-4">';
            html += '<h3 class="text-green-400 font-semibold mb-2">Recommendations</h3>';
            html += '<ul class="list-disc list-inside space-y-2">';
            result.suggestions.forEach((suggestion: any) => {
                if (typeof suggestion === 'object') {
                    if (suggestion.issue && suggestion.suggestions) {
                        // Handle structured suggestions with issue context
                        html += `<li class="text-gray-400 mb-2">`;
                        html += `<span class="font-semibold">${suggestion.issue}:</span>`;
                        html += `<ul class="list-circle list-inside mt-1 ml-4">`;
                        suggestion.suggestions.forEach((s: string) => {
                            html += `<li class="text-gray-300">${s}</li>`;
                        });
                        html += `</ul></li>`;
                    } else {
                        // Handle simple object suggestions
                        html += `<li class="text-gray-300">${suggestion.suggestion || JSON.stringify(suggestion)}</li>`;
                    }
                } else {
                    // Handle string suggestions
                    html += `<li class="text-gray-300">${suggestion}</li>`;
                }
            });
            html += '</ul>';
            html += '</div>';
        }
        
        // Diagnostic Commands
        if (result.diagnostic_commands && result.diagnostic_commands.length > 0) {
            html += '<div class="bg-gray-800 rounded-lg p-4">';
            html += '<h3 class="text-green-400 font-semibold mb-2">Diagnostic Commands</h3>';
            result.diagnostic_commands.forEach((cmd: any) => {
                if (typeof cmd === 'object' && cmd.command) {
                    html += `<div class="mb-2">`;
                    html += `<code class="bg-gray-900 text-yellow-300 px-2 py-1 rounded font-mono text-sm">${cmd.command}</code>`;
                    html += `<p class="text-gray-400 text-sm mt-1">${cmd.description}</p>`;
                    html += `</div>`;
                } else {
                    html += `<div class="mb-2">`;
                    html += `<code class="bg-gray-900 text-yellow-300 px-2 py-1 rounded font-mono text-sm">${cmd}</code>`;
                    html += `</div>`;
                }
            });
            html += '</div>';
        }
        
        html += '</div>';
        return html;
    };

    const handleAnalysis = async () => {
        if (input.trim() === '' || isProcessing) return;
        
        // Check guest limit (5 analyses during beta)
        if (isGuest && guestAnalysisCount >= 5) {
            onUpgradePrompt();
            return;
        }
        
        setIsProcessing(true);
        // Format user input for better display
        let userText = input;
        if (input.length > 500) {
            // For large logs, show a preview with proper formatting
            const lines = input.split('\n');
            const preview = lines.slice(0, 10).join('\n');
            const remainingLines = lines.length - 10;
            userText = `${preview}${remainingLines > 0 ? `\n... (${remainingLines} more lines, ${input.length} total characters)` : ''}`;
        }
        const newOutput = [...output, { type: 'user' as const, text: userText }];
        setOutput(newOutput);
        
        // Add initial processing message
        const processingMessage = { 
            type: 'agent' as const, 
            text: '<div class="bg-gray-800 rounded-lg p-4"><p class="text-gray-300">Starting analysis...</p></div>'
        };
        setOutput([...newOutput, processingMessage]);
        
        try {
            // For guest users, use the simpler non-streaming API
            if (isGuest) {
                // Show analyzing message
                const analyzingMessage = { 
                    type: 'agent' as const, 
                    text: `<div class="bg-gray-800 rounded-lg p-4">
                        <p class="text-gray-300">Analyzing your logs...</p>
                        <div class="mt-2 w-full bg-gray-700 rounded-full h-2">
                            <div class="bg-green-500 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                        </div>
                    </div>`
                };
                setOutput([...newOutput, analyzingMessage]);
                
                // Use non-streaming API
                const result = await analyzeLog({
                    log_content: input,
                    application_name: 'user-app',
                    enable_memory: false
                });
                
                // Format and display the result
                const formattedResult = formatAnalysisResult(result);
                setOutput([...newOutput, { 
                    type: 'agent' as const, 
                    text: formattedResult,
                    analysis: result 
                }]);
                
                // Add to history
                const historyEntry: AnalysisHistory = {
                    id: Date.now().toString(),
                    query: input.substring(0, 100) + (input.length > 100 ? '...' : ''),
                    date: new Date().toISOString().split('T')[0],
                    issues: result.issues?.length || 0,
                    severity: result.issues?.[0]?.severity || 'low',
                    analysis: result
                };
                
                // Update parent component's history state
                const updatedHistory = [historyEntry, ...history];
                setHistory(updatedHistory);
                
                // If not guest, refresh history from server to get proper thread_id
                if (!isGuest) {
                    setTimeout(() => {
                        fetchAnalysisHistory();
                    }, 1000);
                }
                
                // Update guest analysis count
                const newCount = guestAnalysisCount + 1;
                setGuestAnalysisCount(newCount);
                localStorage.setItem('allogator_guest_analysis_count', newCount.toString());
                
                // Add upgrade prompts at strategic points
                if (newCount === 1) {
                    setTimeout(() => {
                        setOutput(prev => [...prev, {
                            type: 'agent',
                            text: `<div class="bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-lg p-4 mt-4">
                                <p class="text-green-300 font-semibold mb-2">🎉 Great analysis!</p>
                                <p class="text-gray-300 text-sm">You have ${5 - newCount} free analyses remaining during our beta. Create an account anytime for unlimited access.</p>
                            </div>`
                        }]);
                    }, 2000);
                } else if (newCount === 3) {
                    setTimeout(() => {
                        setOutput(prev => [...prev, {
                            type: 'agent',
                            text: `<div class="bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border border-blue-500/30 rounded-lg p-4 mt-4">
                                <p class="text-blue-300 font-semibold mb-2">💡 Pro tip</p>
                                <p class="text-gray-300 text-sm">You have ${5 - newCount} free analyses left. Sign up to save your analysis history and unlock advanced features!</p>
                                <a href="/signup" class="inline-block mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors">
                                    Create Free Account
                                </a>
                            </div>`
                        }]);
                    }, 2000);
                } else if (newCount === 5) {
                    setTimeout(() => {
                        setOutput(prev => [...prev, {
                            type: 'agent',
                            text: `<div class="bg-gradient-to-r from-orange-900/20 to-red-900/20 border border-orange-500/30 rounded-lg p-4 mt-4">
                                <p class="text-orange-300 font-semibold mb-2">🚀 That's your 5th free analysis!</p>
                                <p class="text-gray-300 text-sm">You've used all your free beta analyses. Create an account to continue with unlimited access!</p>
                                <a href="/signup" class="inline-block mt-3 px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-lg text-sm font-medium transition-colors">
                                    Sign Up to Continue
                                </a>
                            </div>`
                        }]);
                    }, 2000);
                }
            } else {
                // For authenticated users, use streaming API
                let analysisResult: any = null;
                let progressUpdates: string[] = [];
                
                await analyzeLogStream(
                    {
                        log_content: input,
                        application_name: 'user-app',
                        enable_memory: false,
                        enable_enhanced_analysis: true
                    },
                // onProgress
                (progress) => {
                    console.log('Progress:', progress);
                    progressUpdates.push(`Processing event ${progress.event_number}...`);
                    
                    // Update the processing message with progress
                    const updatedOutput = [...newOutput, {
                        type: 'agent' as const,
                        text: `<div class="bg-gray-800 rounded-lg p-4">
                            <p class="text-gray-300">Analyzing logs...</p>
                            <p class="text-gray-400 text-sm mt-1">${progressUpdates[progressUpdates.length - 1]}</p>
                            <div class="mt-2 w-full bg-gray-700 rounded-full h-2">
                                <div class="bg-green-500 h-2 rounded-full transition-all duration-300" style="width: ${Math.min(progress.event_number * 10, 90)}%"></div>
                            </div>
                        </div>`
                    }];
                    setOutput(updatedOutput);
                },
                // onResult
                (result) => {
                    console.log('Result received:', result);
                    analysisResult = result;
                    
                    // Format and display the result immediately
                    const formattedResult = formatAnalysisResult(result);
                    setOutput([...newOutput, { 
                        type: 'agent' as const, 
                        text: formattedResult,
                        analysis: result 
                    }]);
                },
                // onError
                (error) => {
                    console.error('Streaming error:', error);
                    setOutput([...newOutput, { 
                        type: 'agent' as const, 
                        text: `<div class="bg-red-900/20 border border-red-500 rounded-lg p-4">
                            <p class="text-red-400 font-semibold">Error during analysis</p>
                            <p class="text-gray-300 mt-1">${error.error || 'Unknown error'}</p>
                        </div>` 
                    }]);
                },
                // onComplete
                () => {
                    console.log('Analysis complete');
                    
                    // Add to history if we have a result
                    if (analysisResult) {
                        const historyEntry: AnalysisHistory = {
                            id: Date.now().toString(),
                            query: input.substring(0, 100) + (input.length > 100 ? '...' : ''),
                            date: new Date().toISOString().split('T')[0],
                            issues: analysisResult.issues?.length || 0,
                            severity: analysisResult.issues?.[0]?.severity || 'low',
                            analysis: analysisResult
                        };
                        setHistory([historyEntry, ...history]);
                        
                        // Update guest analysis count
                        if (isGuest) {
                            const newCount = guestAnalysisCount + 1;
                            setGuestAnalysisCount(newCount);
                            localStorage.setItem('allogator_guest_analysis_count', newCount.toString());
                            
                            // Add upgrade prompts at strategic points
                            if (newCount === 1) {
                                setTimeout(() => {
                                    setOutput(prev => [...prev, {
                                        type: 'agent',
                                        text: `<div class="bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-lg p-4 mt-4">
                                            <p class="text-green-300 font-semibold mb-2">🎉 Great analysis!</p>
                                            <p class="text-gray-300 text-sm">You have ${5 - newCount} free analyses remaining during our beta. Create an account anytime for unlimited access.</p>
                                        </div>`
                                    }]);
                                }, 2000);
                            } else if (newCount === 3) {
                                setTimeout(() => {
                                    setOutput(prev => [...prev, {
                                        type: 'agent',
                                        text: `<div class="bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border border-blue-500/30 rounded-lg p-4 mt-4">
                                            <p class="text-blue-300 font-semibold mb-2">💡 Pro tip</p>
                                            <p class="text-gray-300 text-sm">You have ${5 - newCount} free analyses left. Sign up to save your analysis history and unlock advanced features!</p>
                                            <a href="/signup" class="inline-block mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors">
                                                Create Free Account
                                            </a>
                                        </div>`
                                    }]);
                                }, 2000);
                            } else if (newCount === 5) {
                                setTimeout(() => {
                                    setOutput(prev => [...prev, {
                                        type: 'agent',
                                        text: `<div class="bg-gradient-to-r from-orange-900/20 to-red-900/20 border border-orange-500/30 rounded-lg p-4 mt-4">
                                            <p class="text-orange-300 font-semibold mb-2">🚀 That's your 5th free analysis!</p>
                                            <p class="text-gray-300 text-sm">You've used all your free beta analyses. Create an account to continue with unlimited access!</p>
                                            <a href="/signup" class="inline-block mt-3 px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-lg text-sm font-medium transition-colors">
                                                Sign Up to Continue
                                            </a>
                                        </div>`
                                    }]);
                                }, 2000);
                            }
                        }
                    }
                }
            );
            }
            
        } catch (error) {
            setOutput([...newOutput, { 
                type: 'agent' as const, 
                text: `<div class="bg-red-900/20 border border-red-500 rounded-lg p-4">
                    <p class="text-red-400 font-semibold">Error analyzing logs</p>
                    <p class="text-gray-300 mt-1">${error instanceof Error ? error.message : 'Unknown error'}</p>
                    <p class="text-gray-400 text-sm mt-2">Please check that the API server is running at http://localhost:8000</p>
                </div>` 
            }]);
        } finally {
            setIsProcessing(false);
        }

        setInput('');
    };

    return (
        <div className="flex flex-col h-full bg-gray-950 text-gray-200 p-4 md:p-6">
            {/* Guest usage indicator */}
            {isGuest && (
                <div className="mb-4 flex items-center justify-between bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-lg p-3">
                    <div className="flex items-center space-x-3">
                        <SparklesIcon className="w-5 h-5 text-green-400" />
                        <span className="text-sm text-gray-300">
                            Beta Access: <span className="font-semibold text-white">{5 - guestAnalysisCount}</span> free analyses remaining
                        </span>
                    </div>
                    {guestAnalysisCount > 0 && (
                        <a 
                            href="/signup" 
                            className="text-sm text-green-400 hover:text-green-300 transition-colors font-medium"
                        >
                            Sign up for unlimited
                        </a>
                    )}
                </div>
            )}
            
            <div className="flex-grow overflow-y-auto pr-2 space-y-6">
                {output.map((line, index) => (
                    <div key={index}>
                        {line.type === 'user' ? (
                            <div className="flex items-start justify-end">
                                <div className="bg-green-600/80 text-white rounded-lg py-3 px-4 max-w-3xl">
                                    {line.text.includes('\n') || line.text.length > 100 ? (
                                        <pre className="whitespace-pre-wrap font-mono text-sm overflow-x-auto">{line.text}</pre>
                                    ) : (
                                        <p className="whitespace-pre-wrap">{line.text}</p>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-start">
                                <div className="w-8 h-8 mr-3 rounded-full bg-gray-700 flex-shrink-0 flex items-center justify-center">
                                    <AllogatorLogo className="w-5 h-5 text-green-400"/>
                                </div>
                                <div 
                                    className="bg-gray-800 rounded-lg py-2 px-4 max-w-4xl prose prose-invert prose-sm" 
                                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(line.text) }}
                                />
                            </div>
                        )}
                    </div>
                ))}
                {/* Remove the isProcessing block since we handle it in the output messages now */}
                <div ref={outputEndRef} />
            </div>
            <div className="mt-6">
                <div className="flex items-start gap-2 mb-2">
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        accept=".log,.txt,.json"
                        className="hidden"
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg transition-colors"
                    >
                        <UploadIcon className="w-4 h-4" />
                        <span className="text-sm">Upload File</span>
                    </button>
                </div>
                <div className="flex items-start bg-gray-800 border border-gray-700 rounded-lg p-2 focus-within:border-green-500 transition-colors">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.ctrlKey) {
                                e.preventDefault();
                                handleAnalysis();
                            }
                        }}
                        className="flex-grow bg-transparent text-gray-200 ml-2 focus:outline-none w-full resize-none"
                        placeholder={isProcessing ? "Waiting for response..." : "Paste your logs here or describe what you need help with... (Ctrl+Enter to analyze)"}
                        disabled={isProcessing}
                        autoFocus
                        rows={4}
                    />
                    <button 
                        onClick={handleAnalysis} 
                        disabled={isProcessing || !input.trim()} 
                        className="ml-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white font-bold py-2 px-4 rounded transition-colors"
                    >
                        Analyze
                    </button>
                </div>
            </div>
        </div>
    );
};

const History = ({ history }: { history: AnalysisHistory[] }) => {
    const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisHistory | null>(null);
    const [threads, setThreads] = useState<any[]>([]);
    const [isLoadingThreads, setIsLoadingThreads] = useState(false);
    
    useEffect(() => {
        fetchThreads();
    }, []);
    
    const fetchThreads = async () => {
        setIsLoadingThreads(true);
        try {
            const response = await analysisService.getThreads(1, 50);
            setThreads(response.data.threads);
        } catch (error) {
            console.error('Error fetching threads:', error);
        } finally {
            setIsLoadingThreads(false);
        }
    };
    
    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical': return 'text-red-500';
            case 'high': return 'text-orange-500';
            case 'medium': return 'text-yellow-500';
            case 'low': return 'text-blue-500';
            default: return 'text-gray-400';
        }
    };
    
    return (
        <div className="p-6 bg-gray-950 text-gray-200 h-full overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl text-gray-100 font-bold">Analysis History</h1>
                {threads.length > 0 && (
                    <span className="text-sm text-gray-400">{threads.length} analysis threads</span>
                )}
            </div>
            
            {isLoadingThreads ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-400"></div>
                </div>
            ) : threads.length === 0 && history.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-gray-400">No analysis history yet. Start by analyzing some logs!</p>
                </div>
            ) : (
                <div className="border border-gray-800 rounded-lg overflow-hidden">
                    <table className="min-w-full">
                        <thead className="bg-gray-900 border-b-2 border-gray-800">
                            <tr>
                                <th className="p-3 text-left text-sm font-semibold text-gray-400 uppercase tracking-wider">Date</th>
                                <th className="p-3 text-left text-sm font-semibold text-gray-400 uppercase tracking-wider">Log Preview</th>
                                <th className="p-3 text-left text-sm font-semibold text-gray-400 uppercase tracking-wider">Issues</th>
                                <th className="p-3 text-left text-sm font-semibold text-gray-400 uppercase tracking-wider">Severity</th>
                                <th className="p-3 text-left text-sm font-semibold text-gray-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {(threads.length > 0 ? threads : history).map((item: any) => {
                                const isThread = 'thread_id' in item;
                                return (
                                    <tr key={isThread ? item.thread_id : item.id} className="hover:bg-gray-900 transition-colors">
                                        <td className="p-3 text-sm text-gray-300 font-mono">
                                            {isThread 
                                                ? new Date(item.timestamp * 1000).toISOString().split('T')[0]
                                                : item.date}
                                        </td>
                                        <td className="p-3 text-sm text-gray-300 max-w-xs truncate">
                                            {isThread ? item.log_preview : item.query}
                                        </td>
                                        <td className="p-3 text-sm text-gray-300">
                                            {isThread ? item.issue_count : item.issues}
                                        </td>
                                        <td className="p-3 text-sm">
                                            <span className={`font-semibold ${getSeverityColor(item.severity)}`}>
                                                {item.severity.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="p-3 text-sm">
                                            <button 
                                                onClick={() => setSelectedAnalysis(isThread ? {
                                                    id: item.thread_id,
                                                    query: item.log_preview,
                                                    date: new Date(item.timestamp * 1000).toISOString().split('T')[0],
                                                    issues: item.issue_count,
                                                    severity: item.severity,
                                                    analysis: item
                                                } : item)}
                                                className="text-blue-400 hover:underline"
                                            >
                                                View
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
            
            {selectedAnalysis && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
                    <div className="bg-gray-900 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-y-auto p-6">
                        <div className="flex justify-between items-start mb-4">
                            <h2 className="text-xl font-bold text-gray-100">Analysis Details</h2>
                            <button 
                                onClick={() => setSelectedAnalysis(null)}
                                className="text-gray-400 hover:text-white"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="prose prose-invert max-w-none">
                            <div dangerouslySetInnerHTML={{ 
                                __html: DOMPurify.sanitize(formatAnalysisResultForHistory(selectedAnalysis.analysis)) 
                            }} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const formatAnalysisResultForHistory = (result: any) => {
    // Reuse the same formatting function from Dashboard
    let html = '<div class="space-y-4">';
    
    if (result.executive_summary) {
        html += '<div class="bg-gray-800 rounded-lg p-4">';
        html += '<h3 class="text-green-400 font-semibold mb-2">Executive Summary</h3>';
        html += `<p class="text-gray-300">${result.executive_summary.overview || 'Analysis complete.'}</p>`;
        if (result.executive_summary.critical_issues?.length > 0) {
            html += '<div class="mt-2"><span class="text-red-400">Critical Issues:</span><ul class="list-disc list-inside mt-1">';
            result.executive_summary.critical_issues.forEach((issue: string) => {
                html += `<li class="text-gray-300">${issue}</li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';
    }
    
    if (result.issues && result.issues.length > 0) {
        html += '<div class="bg-gray-800 rounded-lg p-4">';
        html += '<h3 class="text-green-400 font-semibold mb-2">Issues Found</h3>';
        result.issues.forEach((issue: any, idx: number) => {
            const severityColor = {
                critical: 'text-red-500',
                high: 'text-orange-500',
                medium: 'text-yellow-500',
                low: 'text-blue-500'
            }[issue.severity] || 'text-gray-400';
            
            html += `<div class="mb-3 pb-3 ${idx < result.issues.length - 1 ? 'border-b border-gray-700' : ''}">`;
            html += `<div class="flex items-center gap-2 mb-1">`;
            html += `<span class="${severityColor} font-semibold">${issue.severity?.toUpperCase()}</span>`;
            html += `<span class="text-gray-400">|</span>`;
            html += `<span class="text-gray-300">${issue.type}</span>`;
            html += `</div>`;
            html += `<p class="text-gray-300">${issue.description}</p>`;
            html += '</div>';
        });
        html += '</div>';
    }
    
    html += '</div>';
    return html;
};

const Applications = () => {
    const apps = [
        { name: 'web-app-01', status: 'HEALTHY', type: 'Kubernetes Pod', lastAnalysis: '2 hours ago' },
        { name: 'api-gateway', status: 'WARNING', type: 'Docker Container', lastAnalysis: '1 day ago' },
        { name: 'user-database', status: 'ERROR', type: 'PostgreSQL', lastAnalysis: '5 minutes ago' },
        { name: 'payment-processor', status: 'HEALTHY', type: 'Lambda Function', lastAnalysis: '3 days ago' },
    ];
    
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'HEALTHY': return 'bg-green-500';
            case 'WARNING': return 'bg-yellow-500';
            case 'ERROR': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    };
    
    return (
        <div className="p-6 bg-gray-950 text-gray-200 h-full overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl text-gray-100 font-bold">Applications</h1>
                <button className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition-colors">
                    + Add Application
                </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {apps.map(app => (
                    <div key={app.name} className="bg-gray-900 p-5 rounded-lg border border-gray-800 hover:border-green-500/50 transition-all cursor-pointer">
                        <div className="flex justify-between items-start">
                            <div>
                                <h2 className="text-lg font-semibold text-gray-100">{app.name}</h2>
                                <p className="text-sm text-gray-400 mt-1">{app.type}</p>
                                <p className="text-xs text-gray-500 mt-2">Last analysis: {app.lastAnalysis}</p>
                            </div>
                            <div className="flex items-center">
                                <div className={`w-2.5 h-2.5 rounded-full mr-2 ${getStatusColor(app.status)}`}></div>
                                <span className="text-xs font-medium text-gray-300">{app.status}</span>
                            </div>
                        </div>
                        <div className="mt-6 flex space-x-2">
                            <button className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 py-1 px-3 rounded">Analyze Logs</button>
                            <button className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 py-1 px-3 rounded">View History</button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const GuestUpgradePrompt = ({ feature }: { feature: string }) => {
    return (
        <div className="flex items-center justify-center h-full p-6">
            <div className="max-w-md text-center">
                <div className="inline-flex p-4 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 mb-6">
                    <SparklesIcon className="w-12 h-12 text-green-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-4">Unlock {feature}</h2>
                <p className="text-gray-400 mb-6">
                    Create a free account to access {feature.toLowerCase()} and all other premium features.
                </p>
                <a 
                    href="/signup" 
                    className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                >
                    Sign Up Free
                    <ArrowRightIcon className="w-5 h-5 ml-2" />
                </a>
                <p className="mt-4 text-sm text-gray-500">No credit card required</p>
            </div>
        </div>
    );
};

const UpgradeModal = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
    if (!isOpen) return null;
    
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-900 rounded-2xl max-w-md w-full p-8 relative">
                <button 
                    onClick={onClose}
                    className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
                >
                    ✕
                </button>
                
                <div className="text-center">
                    <div className="inline-flex p-4 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 mb-6">
                        <SparklesIcon className="w-12 h-12 text-green-400" />
                    </div>
                    
                    <h2 className="text-3xl font-bold text-white mb-4">You've Used Your 5 Free Beta Analyses!</h2>
                    <p className="text-gray-400 mb-8">
                        Sign up for a free account to continue with unlimited log analyses during our beta period.
                    </p>
                    
                    <div className="bg-gray-800/50 rounded-xl p-6 mb-8">
                        <h3 className="text-lg font-semibold text-white mb-4">What you'll get:</h3>
                        <ul className="space-y-3 text-left">
                            <li className="flex items-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-300">Unlimited log analyses</span>
                            </li>
                            <li className="flex items-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-300">Save and search analysis history</span>
                            </li>
                            <li className="flex items-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-300">Configure multiple applications</span>
                            </li>
                            <li className="flex items-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-300">Advanced AI-powered insights</span>
                            </li>
                        </ul>
                    </div>
                    
                    <div className="space-y-3">
                        <a 
                            href="/signup" 
                            className="block w-full py-3 px-6 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-[1.02]"
                        >
                            Create Free Account
                        </a>
                        <button 
                            onClick={onClose}
                            className="block w-full py-3 px-6 bg-gray-800 text-gray-300 font-medium rounded-lg hover:bg-gray-700 hover:text-white transition-all"
                        >
                            Maybe Later
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

const Settings = () => {
    const [settings, setSettings] = useState({
        analysisDepth: 'comprehensive',
        enableMemory: false,
        apiEndpoint: 'http://localhost:8000',
        timeout: 30,
        enableEnhancedAnalysis: true
    });
    
    return (
        <div className="p-6 bg-gray-950 text-gray-200 h-full overflow-y-auto">
            <h1 className="text-2xl text-gray-100 font-bold mb-8">Settings</h1>
            <div className="space-y-10 max-w-2xl">
                <div>
                    <h2 className="text-lg font-semibold text-green-400 pb-2 mb-4">Analysis Configuration</h2>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <label htmlFor="analysis-depth" className="text-gray-300">Analysis Depth</label>
                            <select 
                                id="analysis-depth" 
                                value={settings.analysisDepth}
                                onChange={(e) => setSettings({...settings, analysisDepth: e.target.value})}
                                className="w-48 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                            >
                                <option value="comprehensive">Comprehensive</option>
                                <option value="standard">Standard</option>
                                <option value="quick">Quick</option>
                            </select>
                        </div>
                        <div className="flex items-center justify-between">
                            <label htmlFor="enable-memory" className="text-gray-300">Enable Memory Features</label>
                            <input 
                                type="checkbox" 
                                id="enable-memory" 
                                checked={settings.enableMemory}
                                onChange={(e) => setSettings({...settings, enableMemory: e.target.checked})}
                                className="w-5 h-5 bg-gray-800 border-gray-700 rounded text-green-500 focus:ring-green-500" 
                            />
                        </div>
                        <div className="flex items-center justify-between">
                            <label htmlFor="enable-enhanced" className="text-gray-300">Enhanced Analysis (Recommended)</label>
                            <input 
                                type="checkbox" 
                                id="enable-enhanced" 
                                checked={settings.enableEnhancedAnalysis}
                                onChange={(e) => setSettings({...settings, enableEnhancedAnalysis: e.target.checked})}
                                className="w-5 h-5 bg-gray-800 border-gray-700 rounded text-green-500 focus:ring-green-500" 
                            />
                        </div>
                    </div>
                </div>

                <div>
                    <h2 className="text-lg font-semibold text-green-400 pb-2 mb-4">API Configuration</h2>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <label htmlFor="api-endpoint" className="text-gray-300">API Endpoint</label>
                            <input 
                                type="text" 
                                id="api-endpoint" 
                                value={settings.apiEndpoint}
                                onChange={(e) => setSettings({...settings, apiEndpoint: e.target.value})}
                                className="w-80 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500 font-mono" 
                            />
                        </div>
                        <div className="flex items-center justify-between">
                            <label htmlFor="timeout" className="text-gray-300">Request Timeout (seconds)</label>
                            <input 
                                type="number" 
                                id="timeout" 
                                value={settings.timeout}
                                onChange={(e) => setSettings({...settings, timeout: parseInt(e.target.value)})}
                                className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500" 
                            />
                        </div>
                    </div>
                </div>
                
                <div className="pt-4">
                    <button className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-5 rounded transition-colors w-full md:w-auto">
                        Save Changes
                    </button>
                </div>
            </div>
        </div>
    );
};


// --- Main App Component ---

interface AllogatorUIProps {
    isGuest?: boolean;
}

export default function AllogatorUI({ isGuest = false }: AllogatorUIProps) {
    const [activeView, setActiveView] = useState('Dashboard');
    const [history, setHistory] = useState<AnalysisHistory[]>([]);
    const [guestAnalysisCount, setGuestAnalysisCount] = useState(() => {
        const count = localStorage.getItem('allogator_guest_analysis_count');
        return count ? parseInt(count) : 0;
    });
    const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    // Add Google Font for a cleaner look
    useEffect(() => {
        const link = document.createElement('link');
        link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono&display=swap';
        link.rel = 'stylesheet';
        document.head.appendChild(link);
    }, []);

    // Fetch analysis history for authenticated users
    useEffect(() => {
        if (!isGuest) {
            fetchAnalysisHistory();
        }
    }, [isGuest]);

    const fetchAnalysisHistory = async () => {
        setIsLoadingHistory(true);
        try {
            const response = await analysisService.getHistory(1, 50);
            const historyData = response.data.analyses.map((analysis: any) => ({
                id: analysis.analysis_id || Date.now().toString(),
                query: analysis.log_source || 'Log Analysis',
                date: new Date(analysis.timestamp).toISOString().split('T')[0],
                issues: analysis.issue_count || 0,
                severity: analysis.severity || 'low',
                analysis: analysis
            }));
            setHistory(historyData);
        } catch (error) {
            console.error('Error fetching history:', error);
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const renderView = () => {
        switch (activeView) {
            case 'Dashboard':
                return (
                    <Dashboard 
                        isGuest={isGuest}
                        guestAnalysisCount={guestAnalysisCount}
                        setGuestAnalysisCount={setGuestAnalysisCount}
                        onUpgradePrompt={() => setShowUpgradePrompt(true)}
                        history={history}
                        setHistory={setHistory}
                        fetchAnalysisHistory={fetchAnalysisHistory}
                    />
                );
            case 'History':
                return isGuest ? <GuestUpgradePrompt feature="History" /> : <History history={history} />;
            case 'Applications':
                return isGuest ? <GuestUpgradePrompt feature="Applications" /> : <Applications />;
            case 'Settings':
                return isGuest ? <GuestUpgradePrompt feature="Settings" /> : <Settings />;
            default:
                return (
                    <Dashboard 
                        isGuest={isGuest}
                        guestAnalysisCount={guestAnalysisCount}
                        setGuestAnalysisCount={setGuestAnalysisCount}
                        onUpgradePrompt={() => setShowUpgradePrompt(true)}
                        history={history}
                        setHistory={setHistory}
                        fetchAnalysisHistory={fetchAnalysisHistory}
                    />
                );
        }
    };

    return (
        <div className="flex h-screen bg-gray-950 font-sans">
            <style>{`
                .prose { --tw-prose-body: #d1d5db; --tw-prose-headings: #f9fafb; --tw-prose-links: #60a5fa; --tw-prose-bold: #f9fafb; --tw-prose-code: #fcd34d; }
                .font-sans { font-family: 'Inter', sans-serif; }
                .font-mono { font-family: 'Roboto Mono', monospace; }
            `}</style>
            <Sidebar activeView={activeView} setActiveView={setActiveView} isGuest={isGuest} />
            <main className="flex-1 h-full overflow-hidden">
                {renderView()}
            </main>
            <UpgradeModal isOpen={showUpgradePrompt} onClose={() => setShowUpgradePrompt(false)} />
        </div>
    );
}