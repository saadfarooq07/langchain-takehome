import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

// --- SVG Icons ---
const AllogatorLogo = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M16.596 4.5H7.404L3 12l4.404 7.5h9.192L21 12l-4.404-7.5zM15.07 16.5H8.93l-3.536-6 3.536-6h6.14l3.536 6-3.536 6z" />
        <path d="M13.895 8.25h-3.79l-1.5 2.598 1.5 2.598h3.79l1.5-2.598-1.5-2.598z" />
    </svg>
);

const CheckIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
);

const ArrowRightIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
    </svg>
);

const SparklesIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3L14.5 8.5L20 11L14.5 13.5L12 19L9.5 13.5L4 11L9.5 8.5L12 3Z" />
        <path d="M5 3L6 5L8 6L6 7L5 9L4 7L2 6L4 5L5 3Z" />
        <path d="M19 15L20 17L22 18L20 19L19 21L18 19L16 18L18 17L19 15Z" />
    </svg>
);

const ZapIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
    </svg>
);

const ShieldIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
    </svg>
);

const GlobeIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="2" y1="12" x2="22" y2="12"></line>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
    </svg>
);

export default function LandingPage() {
    const [scrolled, setScrolled] = useState(false);
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };

        const handleMouseMove = (e: MouseEvent) => {
            setMousePosition({ x: e.clientX, y: e.clientY });
        };

        window.addEventListener('scroll', handleScroll);
        window.addEventListener('mousemove', handleMouseMove);

        return () => {
            window.removeEventListener('scroll', handleScroll);
            window.removeEventListener('mousemove', handleMouseMove);
        };
    }, []);

    const features = [
        {
            icon: SparklesIcon,
            title: "Smart Log Analysis",
            description: "AI-powered analysis identifies errors, patterns, and provides actionable recommendations instantly",
            gradient: "from-purple-500 to-pink-500"
        },
        {
            icon: ZapIcon,
            title: "Lightning Fast",
            description: "Handle logs over 10MB with memory-efficient streaming and parallel chunk processing",
            gradient: "from-yellow-500 to-orange-500"
        },
        {
            icon: ShieldIcon,
            title: "Enterprise Ready",
            description: "Built-in reliability with circuit breakers, rate limiting, and automatic retries",
            gradient: "from-blue-500 to-cyan-500"
        },
        {
            icon: GlobeIcon,
            title: "Domain Expertise",
            description: "Specialized analyzers for HDFS, security logs, and application-specific patterns",
            gradient: "from-green-500 to-emerald-500"
        }
    ];

    const steps = [
        {
            number: "01",
            title: "Upload Your Logs",
            description: "Paste logs directly or upload files up to 100MB"
        },
        {
            number: "02",
            title: "AI Analysis",
            description: "Our dual-model architecture analyzes patterns and issues"
        },
        {
            number: "03",
            title: "Get Solutions",
            description: "Receive actionable insights with documentation references"
        }
    ];

    const betaFeatures = [
        {
            icon: SparklesIcon,
            title: "Free During Beta",
            description: "Get unlimited access to all features while we're in beta. Help us improve!"
        },
        {
            icon: ZapIcon,
            title: "Early Access",
            description: "Be among the first to use cutting-edge AI log analysis technology"
        },
        {
            icon: ShieldIcon,
            title: "Shape the Future",
            description: "Your feedback directly influences our product development"
        }
    ];

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100 overflow-x-hidden">
            {/* Animated background gradient */}
            <div className="fixed inset-0 opacity-30">
                <div 
                    className="absolute inset-0 bg-gradient-to-br from-green-900/20 via-transparent to-purple-900/20"
                    style={{
                        transform: `translate(${mousePosition.x * 0.01}px, ${mousePosition.y * 0.01}px)`
                    }}
                />
            </div>

            {/* Navigation */}
            <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${
                scrolled ? 'bg-gray-950/80 backdrop-blur-lg border-b border-gray-800' : ''
            }`}>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center space-x-3">
                            <AllogatorLogo className="h-8 w-8 text-green-400" />
                            <span className="text-xl font-bold bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
                                Allogator
                            </span>
                        </div>
                        <div className="hidden md:flex items-center space-x-8">
                            <a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a>
                            <a href="#how-it-works" className="text-gray-300 hover:text-white transition-colors">How it Works</a>
                            <Link 
                                to="/login" 
                                className="text-gray-300 hover:text-white transition-colors"
                            >
                                Sign In
                            </Link>
                            <div className="flex items-center space-x-3">
                                <span className="text-xs text-green-400 font-medium bg-green-400/10 px-3 py-1 rounded-full">BETA</span>
                                <Link 
                                    to="/app" 
                                    className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-2 rounded-lg font-medium hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                                >
                                    Get Started
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center">
                        <div className="inline-flex items-center space-x-2 bg-gradient-to-r from-green-900/30 to-emerald-900/30 backdrop-blur-sm border border-green-500/20 rounded-full px-4 py-2 mb-8">
                            <SparklesIcon className="w-4 h-4 text-green-400" />
                            <span className="text-sm text-green-400">Beta • Powered by Gemini 2.5 & Kimi K2</span>
                        </div>
                        
                        <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
                            <span className="bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                                Transform Your Logs Into
                            </span>
                            <br />
                            <span className="bg-gradient-to-r from-green-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                                Actionable Insights
                            </span>
                        </h1>
                        
                        <p className="text-xl md:text-2xl text-gray-400 mb-12 max-w-3xl mx-auto">
                            AI-powered log analysis that identifies issues, suggests solutions, and helps you fix problems faster than ever before.
                        </p>
                        
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link 
                                to="/app" 
                                className="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-medium text-white bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl overflow-hidden transition-all duration-300 hover:scale-105"
                            >
                                <span className="relative z-10 flex items-center">
                                    Try It Now - No Signup
                                    <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                                </span>
                                <div className="absolute inset-0 bg-gradient-to-r from-green-600 to-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </Link>
                            
                            <Link 
                                to="/signup" 
                                className="inline-flex items-center justify-center px-8 py-4 text-lg font-medium text-gray-300 bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl hover:bg-gray-800 hover:text-white transition-all duration-300"
                            >
                                Sign Up for Unlimited
                            </Link>
                        </div>
                        
                        <p className="mt-6 text-sm text-gray-500">
                            ✨ Free during beta • Analyze up to 5 logs instantly • No signup required
                        </p>
                    </div>

                    {/* Hero Image/Animation */}
                    <div className="mt-20 relative">
                        <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-transparent to-transparent z-10" />
                        <div className="relative bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl border border-gray-700 p-8 overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-green-500/20 rounded-full blur-3xl" />
                            <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl" />
                            
                            <div className="relative z-20 font-mono text-sm">
                                <div className="text-gray-400 mb-2">[2024-01-20 14:25:12] Starting log analysis...</div>
                                <div className="text-green-400 mb-2">✓ Detected 3 critical issues</div>
                                <div className="text-yellow-400 mb-2">⚠ Database connection timeout at line 1247</div>
                                <div className="text-blue-400">→ Suggested fix: Increase connection pool size</div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl md:text-5xl font-bold mb-4">
                            <span className="bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                                Powerful Features
                            </span>
                        </h2>
                        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                            Everything you need to analyze, understand, and fix issues in your logs
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {features.map((feature, index) => (
                            <div 
                                key={index}
                                className="group relative bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition-all duration-300"
                            >
                                <div className="absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity rounded-2xl"
                                     style={{
                                         backgroundImage: `linear-gradient(to bottom right, var(--tw-gradient-stops))`,
                                         '--tw-gradient-from': feature.gradient.split(' ')[1],
                                         '--tw-gradient-to': feature.gradient.split(' ')[3]
                                     } as React.CSSProperties}
                                />
                                
                                <div className={`inline-flex p-3 rounded-xl bg-gradient-to-br ${feature.gradient} mb-6`}>
                                    <feature.icon className="w-6 h-6 text-white" />
                                </div>
                                
                                <h3 className="text-2xl font-semibold mb-3 text-white">{feature.title}</h3>
                                <p className="text-gray-400 leading-relaxed">{feature.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* How it Works Section */}
            <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-900/30">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl md:text-5xl font-bold mb-4">
                            <span className="bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                                How It Works
                            </span>
                        </h2>
                        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                            Get started in minutes with our simple three-step process
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {steps.map((step, index) => (
                            <div key={index} className="relative">
                                {index < steps.length - 1 && (
                                    <div className="hidden md:block absolute top-1/2 left-full w-full h-0.5 bg-gradient-to-r from-gray-700 to-transparent -translate-y-1/2 z-0" />
                                )}
                                
                                <div className="relative z-10 text-center">
                                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30 mb-6">
                                        <span className="text-3xl font-bold text-green-400">{step.number}</span>
                                    </div>
                                    
                                    <h3 className="text-xl font-semibold mb-3 text-white">{step.title}</h3>
                                    <p className="text-gray-400">{step.description}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Beta Section */}
            <section id="beta" className="py-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center space-x-2 bg-gradient-to-r from-green-900/30 to-emerald-900/30 backdrop-blur-sm border border-green-500/20 rounded-full px-6 py-3 mb-6">
                            <SparklesIcon className="w-5 h-5 text-green-400" />
                            <span className="text-lg font-semibold text-green-400">Currently in Beta</span>
                        </div>
                        
                        <h2 className="text-4xl md:text-5xl font-bold mb-4">
                            <span className="bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                                Join Our Beta Program
                            </span>
                        </h2>
                        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                            Experience the future of log analysis. Free access to all features during our beta period.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                        {betaFeatures.map((feature, index) => (
                            <div 
                                key={index}
                                className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition-all duration-300"
                            >
                                <div className="inline-flex p-3 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 mb-6">
                                    <feature.icon className="w-6 h-6 text-green-400" />
                                </div>
                                
                                <h3 className="text-xl font-semibold mb-3 text-white">{feature.title}</h3>
                                <p className="text-gray-400">{feature.description}</p>
                            </div>
                        ))}
                    </div>

                    <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl border border-gray-700 p-8 md:p-12 text-center">
                        <h3 className="text-2xl font-bold text-white mb-4">What's Included in Beta?</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto mb-8">
                            <div className="flex items-center justify-center md:justify-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3" />
                                <span className="text-gray-300">Unlimited log analyses</span>
                            </div>
                            <div className="flex items-center justify-center md:justify-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3" />
                                <span className="text-gray-300">All AI features</span>
                            </div>
                            <div className="flex items-center justify-center md:justify-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3" />
                                <span className="text-gray-300">Priority support</span>
                            </div>
                            <div className="flex items-center justify-center md:justify-start">
                                <CheckIcon className="w-5 h-5 text-green-400 mr-3" />
                                <span className="text-gray-300">Early feature access</span>
                            </div>
                        </div>
                        
                        <p className="text-gray-400 mb-6">
                            No credit card required. Just sign up and start analyzing.
                        </p>
                        
                        <Link 
                            to="/app" 
                            className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-xl hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                        >
                            Try It Now
                            <ArrowRightIcon className="w-5 h-5 ml-2" />
                        </Link>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-4xl mx-auto">
                    <div className="relative bg-gradient-to-br from-green-900/20 to-emerald-900/20 backdrop-blur-sm border border-green-500/20 rounded-3xl p-12 text-center overflow-hidden">
                        <div className="absolute top-0 right-0 w-96 h-96 bg-green-500/10 rounded-full blur-3xl" />
                        <div className="absolute bottom-0 left-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
                        
                        <div className="relative z-10">
                            <h2 className="text-4xl md:text-5xl font-bold mb-6">
                                <span className="bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
                                    Ready to Transform Your Log Analysis?
                                </span>
                            </h2>
                            <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
                                Join thousands of developers who are already using Allogator to debug faster and ship with confidence.
                            </p>
                            
                            <div className="flex flex-col sm:flex-row gap-4 justify-center">
                                <Link 
                                    to="/app" 
                                    className="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-medium text-white bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl overflow-hidden transition-all duration-300 hover:scale-105"
                                >
                                    <span className="relative z-10 flex items-center">
                                        Try It Now
                                        <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                                    </span>
                                    <div className="absolute inset-0 bg-gradient-to-r from-green-600 to-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </Link>
                                
                                <Link 
                                    to="/signup" 
                                    className="inline-flex items-center justify-center px-8 py-4 text-lg font-medium text-gray-300 bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl hover:bg-gray-800 hover:text-white transition-all duration-300"
                                >
                                    Create Free Account
                                </Link>
                            </div>
                            
                            <p className="mt-4 text-sm text-gray-400">
                                Beta Access • Analyze 5 logs free • Then unlimited with account
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-gray-800 py-12 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row justify-between items-center">
                        <div className="flex items-center space-x-3 mb-4 md:mb-0">
                            <AllogatorLogo className="h-6 w-6 text-green-400" />
                            <span className="text-lg font-semibold text-gray-300">Allogator</span>
                        </div>
                        
                        <div className="flex space-x-8 text-sm text-gray-400">
                            <a href="#" className="hover:text-white transition-colors">Privacy</a>
                            <a href="#" className="hover:text-white transition-colors">Terms</a>
                            <a href="#" className="hover:text-white transition-colors">Documentation</a>
                            <a href="#" className="hover:text-white transition-colors">Contact</a>
                        </div>
                    </div>
                    
                    <div className="mt-8 pt-8 border-t border-gray-800 text-center text-sm text-gray-500">
                        © 2024 Allogator. All rights reserved.
                    </div>
                </div>
            </footer>
        </div>
    );
}