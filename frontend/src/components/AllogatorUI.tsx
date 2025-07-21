import React, { useState, useEffect, useRef } from 'react';
import { analyzeLog, analyzeLogStream } from '../services/api';
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

// --- Components ---

const Sidebar = ({ activeView, setActiveView }: { activeView: string; setActiveView: (view: string) => void }) => {
    const navItems = [
        { name: 'Dashboard', icon: TerminalIcon },
        { name: 'History', icon: HistoryIcon },
        { name: 'Applications', icon: AppsIcon },
        { name: 'Settings', icon: SettingsIcon },
    ];

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
                <div className="flex items-center">
                    <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center font-bold text-gray-900">
                        U
                    </div>
                    <div className="hidden md:block ml-3">
                        <p className="text-sm font-semibold text-white">User</p>
                        <span className="text-xs text-green-400">READY</span>
                    </div>
                </div>
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

const Dashboard = () => {
    const [input, setInput] = useState('');
    const [output, setOutput] = useState<AnalysisMessage[]>([
      { type: 'agent', text: 'Log Analyzer is ready. Paste your logs or upload a file to begin analysis.' },
    ]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [history, setHistory] = useState<AnalysisHistory[]>([]);
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
                    html += `<span class="text-gray-300">${issue.type}</span>`;
                }
                html += `</div>`;
                html += `<p class="text-gray-300">${issue.description}</p>`;
                if (issue.root_cause) {
                    html += `<p class="text-sm text-gray-400 mt-1"><strong>Root Cause:</strong> ${issue.root_cause}</p>`;
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
        
        setIsProcessing(true);
        const newOutput = [...output, { type: 'user' as const, text: input.length > 500 ? `[Log file: ${input.length} characters]` : input }];
        setOutput(newOutput);
        
        // Add initial processing message
        const processingMessage = { 
            type: 'agent' as const, 
            text: '<div class="bg-gray-800 rounded-lg p-4"><p class="text-gray-300">Starting analysis...</p></div>'
        };
        setOutput([...newOutput, processingMessage]);
        
        try {
            let analysisResult: any = null;
            let progressUpdates: string[] = [];
            
            // Use streaming API
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
                    }
                }
            );
            
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
            <div className="flex-grow overflow-y-auto pr-2 space-y-6">
                {output.map((line, index) => (
                    <div key={index}>
                        {line.type === 'user' ? (
                            <div className="flex items-start justify-end">
                                <p className="bg-green-600/80 text-white rounded-lg py-2 px-4 max-w-xl whitespace-pre-wrap">{line.text}</p>
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
            <h1 className="text-2xl text-gray-100 font-bold mb-6">Analysis History</h1>
            {history.length === 0 ? (
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
                            {history.map(session => (
                                <tr key={session.id} className="hover:bg-gray-900 transition-colors">
                                    <td className="p-3 text-sm text-gray-300 font-mono">{session.date}</td>
                                    <td className="p-3 text-sm text-gray-300 max-w-xs truncate">{session.query}</td>
                                    <td className="p-3 text-sm text-gray-300">{session.issues}</td>
                                    <td className="p-3 text-sm">
                                        <span className={`font-semibold ${getSeverityColor(session.severity)}`}>
                                            {session.severity.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="p-3 text-sm">
                                        <button 
                                            onClick={() => setSelectedAnalysis(session)}
                                            className="text-blue-400 hover:underline"
                                        >
                                            View
                                        </button>
                                    </td>
                                </tr>
                            ))}
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

export default function AllogatorUI() {
    const [activeView, setActiveView] = useState('Dashboard');
    const [history, setHistory] = useState<AnalysisHistory[]>([]);

    // Add Google Font for a cleaner look
    useEffect(() => {
        const link = document.createElement('link');
        link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono&display=swap';
        link.rel = 'stylesheet';
        document.head.appendChild(link);
    }, []);

    const renderView = () => {
        switch (activeView) {
            case 'Dashboard':
                return <Dashboard />;
            case 'History':
                return <History history={history} />;
            case 'Applications':
                return <Applications />;
            case 'Settings':
                return <Settings />;
            default:
                return <Dashboard />;
        }
    };

    return (
        <div className="flex h-screen bg-gray-950 font-sans">
            <style>{`
                .prose { --tw-prose-body: #d1d5db; --tw-prose-headings: #f9fafb; --tw-prose-links: #60a5fa; --tw-prose-bold: #f9fafb; --tw-prose-code: #fcd34d; }
                .font-sans { font-family: 'Inter', sans-serif; }
                .font-mono { font-family: 'Roboto Mono', monospace; }
            `}</style>
            <Sidebar activeView={activeView} setActiveView={setActiveView} />
            <main className="flex-1 h-full overflow-hidden">
                {renderView()}
            </main>
        </div>
    );
}