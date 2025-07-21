import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, storeApiKeys } from '../services/api';

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

const ArrowLeftIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="19" y1="12" x2="5" y2="12"></line>
        <polyline points="12 19 5 12 12 5"></polyline>
    </svg>
);

const KeyIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
    </svg>
);

const UserIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
    </svg>
);

const SparklesIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3L14.5 8.5L20 11L14.5 13.5L12 19L9.5 13.5L4 11L9.5 8.5L12 3Z" />
        <path d="M5 3L6 5L8 6L6 7L5 9L4 7L2 6L4 5L5 3Z" />
        <path d="M19 15L20 17L22 18L20 19L19 21L18 19L16 18L18 17L19 15Z" />
    </svg>
);

const CopyIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
    </svg>
);

const ExternalLinkIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
        <polyline points="15 3 21 3 21 9"></polyline>
        <line x1="10" y1="14" x2="21" y2="3"></line>
    </svg>
);

interface FormData {
    fullName: string;
    email: string;
    password: string;
    confirmPassword: string;
    company: string;
}

export default function OnboardingWizard() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState<FormData>({
        fullName: '',
        email: '',
        password: '',
        confirmPassword: '',
        company: ''
    });
    const [errors, setErrors] = useState<Partial<FormData>>({});
    const [isCreatingAccount, setIsCreatingAccount] = useState(false);

    const validateStep = (step: number): boolean => {
        const newErrors: Partial<FormData> = {};

        if (step === 2) {
            if (!formData.fullName.trim()) newErrors.fullName = 'Full name is required';
            if (!formData.email.trim()) newErrors.email = 'Email is required';
            else if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = 'Invalid email format';
            if (!formData.password.trim()) newErrors.password = 'Password is required';
            else if (formData.password.length < 8) newErrors.password = 'Password must be at least 8 characters';
            if (!formData.confirmPassword.trim()) newErrors.confirmPassword = 'Please confirm your password';
            else if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Passwords do not match';
            if (!formData.role.trim()) newErrors.role = 'Please select a role';
        }

        if (step === 3) {
            if (!formData.geminiApiKey.trim()) newErrors.geminiApiKey = 'Gemini API key is required';
            if (!formData.groqApiKey.trim()) newErrors.groqApiKey = 'Groq API key is required';
            if (!formData.tavilyApiKey.trim()) newErrors.tavilyApiKey = 'Tavily API key is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleNext = async () => {
        if (validateStep(currentStep)) {
            if (currentStep === 2) {
                // Create tenant and user account
                setIsCreatingAccount(true);
                try {
                    // Generate a tenant slug from company name or email
                    const tenantSlug = formData.company 
                        ? formData.company.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')
                        : formData.email.split('@')[0].toLowerCase().replace(/[^a-z0-9]/g, '-');
                    
                    const tenantName = formData.company || `${formData.fullName}'s Workspace`;
                    
                    // Create tenant with owner
                    await authService.createTenant({
                        name: tenantName,
                        slug: tenantSlug,
                        owner_email: formData.email,
                        owner_password: formData.password,
                        owner_name: formData.fullName,
                        description: `${formData.role} at ${formData.company || 'Independent'}`
                    });
                    
                    // Auto-login after successful registration
                    await authService.login(formData.email, formData.password, tenantSlug);
                    
                    setCurrentStep(prev => Math.min(prev + 1, totalSteps));
                } catch (error: any) {
                    setErrors({ email: error.message || 'Failed to create account. Please try again.' });
                } finally {
                    setIsCreatingAccount(false);
                }
            } else if (currentStep === 3) {
                // Save API keys
                await storeApiKeys({
                    gemini: formData.geminiApiKey,
                    groq: formData.groqApiKey,
                    tavily: formData.tavilyApiKey
                });
                setCurrentStep(prev => Math.min(prev + 1, totalSteps));
            } else {
                setCurrentStep(prev => Math.min(prev + 1, totalSteps));
            }
        }
    };

    const handlePrevious = () => {
        setCurrentStep(prev => Math.max(prev - 1, 1));
    };

    const handleInputChange = (field: keyof FormData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: undefined }));
        }
    };

    const copyToClipboard = (text: string, keyName: string) => {
        navigator.clipboard.writeText(text);
        setCopiedKey(keyName);
        setTimeout(() => setCopiedKey(null), 2000);
    };

    const runDemoAnalysis = () => {
        setIsAnalyzing(true);
        // Simulate analysis
        setTimeout(() => {
            setIsAnalyzing(false);
            setAnalysisComplete(true);
        }, 3000);
    };

    const completeOnboarding = () => {
        // User data is already saved during login
        // Navigate to the main app
        navigate('/app');
    };

    const renderStepContent = () => {
        switch (currentStep) {
            case 1:
                return (
                    <div className="text-center space-y-6">
                        <div className="inline-flex p-4 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 mb-4">
                            <SparklesIcon className="w-16 h-16 text-green-400" />
                        </div>
                        
                        <h2 className="text-3xl font-bold text-white">Welcome to Allogator!</h2>
                        <p className="text-xl text-gray-400 max-w-md mx-auto">
                            Let's get you set up in just a few minutes. We'll help you configure everything you need to start analyzing logs like a pro.
                        </p>
                        
                        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6 max-w-md mx-auto">
                            <h3 className="text-lg font-semibold text-white mb-4">What we'll do together:</h3>
                            <ul className="space-y-3 text-left">
                                <li className="flex items-start">
                                    <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                    <span className="text-gray-300">Create your account</span>
                                </li>
                                <li className="flex items-start">
                                    <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                    <span className="text-gray-300">Configure API keys</span>
                                </li>
                                <li className="flex items-start">
                                    <CheckIcon className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
                                    <span className="text-gray-300">Run your first analysis</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                );

            case 2:
                return (
                    <div className="space-y-6 max-w-md mx-auto">
                        <div className="text-center mb-8">
                            <h2 className="text-3xl font-bold text-white mb-2">Create Your Account</h2>
                            <p className="text-gray-400">Tell us a bit about yourself</p>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-2">
                                    Full Name *
                                </label>
                                <input
                                    type="text"
                                    id="fullName"
                                    value={formData.fullName}
                                    onChange={(e) => handleInputChange('fullName', e.target.value)}
                                    className={`w-full px-4 py-3 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all ${
                                        errors.fullName ? 'border-red-500' : 'border-gray-700'
                                    }`}
                                    placeholder="John Doe"
                                />
                                {errors.fullName && (
                                    <p className="mt-1 text-sm text-red-400">{errors.fullName}</p>
                                )}
                            </div>

                            <div>
                                <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                    Email Address *
                                </label>
                                <input
                                    type="email"
                                    id="email"
                                    value={formData.email}
                                    onChange={(e) => handleInputChange('email', e.target.value)}
                                    className={`w-full px-4 py-3 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all ${
                                        errors.email ? 'border-red-500' : 'border-gray-700'
                                    }`}
                                    placeholder="john@company.com"
                                />
                                {errors.email && (
                                    <p className="mt-1 text-sm text-red-400">{errors.email}</p>
                                )}
                            </div>

                            <div>
                                <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                                    Password *
                                </label>
                                <input
                                    type="password"
                                    id="password"
                                    value={formData.password}
                                    onChange={(e) => handleInputChange('password', e.target.value)}
                                    className={`w-full px-4 py-3 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all ${
                                        errors.password ? 'border-red-500' : 'border-gray-700'
                                    }`}
                                    placeholder="••••••••"
                                />
                                {errors.password && (
                                    <p className="mt-1 text-sm text-red-400">{errors.password}</p>
                                )}
                            </div>

                            <div>
                                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                                    Confirm Password *
                                </label>
                                <input
                                    type="password"
                                    id="confirmPassword"
                                    value={formData.confirmPassword}
                                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                                    className={`w-full px-4 py-3 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all ${
                                        errors.confirmPassword ? 'border-red-500' : 'border-gray-700'
                                    }`}
                                    placeholder="••••••••"
                                />
                                {errors.confirmPassword && (
                                    <p className="mt-1 text-sm text-red-400">{errors.confirmPassword}</p>
                                )}
                            </div>

                            <div>
                                <label htmlFor="company" className="block text-sm font-medium text-gray-300 mb-2">
                                    Company (Optional)
                                </label>
                                <input
                                    type="text"
                                    id="company"
                                    value={formData.company}
                                    onChange={(e) => handleInputChange('company', e.target.value)}
                                    className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all"
                                    placeholder="Acme Corp"
                                />
                            </div>

                            <div>
                                <label htmlFor="role" className="block text-sm font-medium text-gray-300 mb-2">
                                    Your Role *
                                </label>
                                <select
                                    id="role"
                                    value={formData.role}
                                    onChange={(e) => handleInputChange('role', e.target.value)}
                                    className={`w-full px-4 py-3 bg-gray-800 border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500 transition-all ${
                                        errors.role ? 'border-red-500' : 'border-gray-700'
                                    }`}
                                >
                                    <option value="">Select your role</option>
                                    <option value="developer">Developer</option>
                                    <option value="devops">DevOps Engineer</option>
                                    <option value="sre">Site Reliability Engineer</option>
                                    <option value="architect">Software Architect</option>
                                    <option value="manager">Engineering Manager</option>
                                    <option value="other">Other</option>
                                </select>
                                {errors.role && (
                                    <p className="mt-1 text-sm text-red-400">{errors.role}</p>
                                )}
                            </div>
                        </div>
                    </div>
                );

            case 3:
                return (
                    <div className="space-y-6 max-w-2xl mx-auto">
                        <div className="text-center mb-8">
                            <h2 className="text-3xl font-bold text-white mb-2">Configure API Keys</h2>
                            <p className="text-gray-400">Connect your AI services to power the analysis</p>
                        </div>

                        <div className="space-y-6">
                            {/* Gemini API Key */}
                            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-white mb-1">Gemini API Key</h3>
                                        <p className="text-sm text-gray-400">For analyzing large log files</p>
                                    </div>
                                    <a
                                        href="https://makersuite.google.com/app/apikey"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center text-sm text-green-400 hover:text-green-300 transition-colors"
                                    >
                                        Get API Key
                                        <ExternalLinkIcon className="w-4 h-4 ml-1" />
                                    </a>
                                </div>
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={formData.geminiApiKey}
                                        onChange={(e) => handleInputChange('geminiApiKey', e.target.value)}
                                        className={`w-full px-4 py-3 bg-gray-900 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all font-mono text-sm ${
                                            errors.geminiApiKey ? 'border-red-500' : 'border-gray-700'
                                        }`}
                                        placeholder="AIza..."
                                    />
                                    <button
                                        type="button"
                                        onClick={() => copyToClipboard(formData.geminiApiKey, 'gemini')}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                                    >
                                        {copiedKey === 'gemini' ? (
                                            <CheckIcon className="w-5 h-5 text-green-400" />
                                        ) : (
                                            <CopyIcon className="w-5 h-5" />
                                        )}
                                    </button>
                                </div>
                                {errors.geminiApiKey && (
                                    <p className="mt-2 text-sm text-red-400">{errors.geminiApiKey}</p>
                                )}
                            </div>

                            {/* Groq API Key */}
                            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-white mb-1">Groq API Key</h3>
                                        <p className="text-sm text-gray-400">For orchestrating agent tasks</p>
                                    </div>
                                    <a
                                        href="https://console.groq.com/keys"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center text-sm text-green-400 hover:text-green-300 transition-colors"
                                    >
                                        Get API Key
                                        <ExternalLinkIcon className="w-4 h-4 ml-1" />
                                    </a>
                                </div>
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={formData.groqApiKey}
                                        onChange={(e) => handleInputChange('groqApiKey', e.target.value)}
                                        className={`w-full px-4 py-3 bg-gray-900 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all font-mono text-sm ${
                                            errors.groqApiKey ? 'border-red-500' : 'border-gray-700'
                                        }`}
                                        placeholder="gsk_..."
                                    />
                                    <button
                                        type="button"
                                        onClick={() => copyToClipboard(formData.groqApiKey, 'groq')}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                                    >
                                        {copiedKey === 'groq' ? (
                                            <CheckIcon className="w-5 h-5 text-green-400" />
                                        ) : (
                                            <CopyIcon className="w-5 h-5" />
                                        )}
                                    </button>
                                </div>
                                {errors.groqApiKey && (
                                    <p className="mt-2 text-sm text-red-400">{errors.groqApiKey}</p>
                                )}
                            </div>

                            {/* Tavily API Key */}
                            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-white mb-1">Tavily API Key</h3>
                                        <p className="text-sm text-gray-400">For searching documentation</p>
                                    </div>
                                    <a
                                        href="https://tavily.com"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center text-sm text-green-400 hover:text-green-300 transition-colors"
                                    >
                                        Get API Key
                                        <ExternalLinkIcon className="w-4 h-4 ml-1" />
                                    </a>
                                </div>
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={formData.tavilyApiKey}
                                        onChange={(e) => handleInputChange('tavilyApiKey', e.target.value)}
                                        className={`w-full px-4 py-3 bg-gray-900 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all font-mono text-sm ${
                                            errors.tavilyApiKey ? 'border-red-500' : 'border-gray-700'
                                        }`}
                                        placeholder="tvly-..."
                                    />
                                    <button
                                        type="button"
                                        onClick={() => copyToClipboard(formData.tavilyApiKey, 'tavily')}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                                    >
                                        {copiedKey === 'tavily' ? (
                                            <CheckIcon className="w-5 h-5 text-green-400" />
                                        ) : (
                                            <CopyIcon className="w-5 h-5" />
                                        )}
                                    </button>
                                </div>
                                {errors.tavilyApiKey && (
                                    <p className="mt-2 text-sm text-red-400">{errors.tavilyApiKey}</p>
                                )}
                            </div>
                        </div>

                        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                            <p className="text-sm text-blue-300">
                                <strong>Note:</strong> Your API keys are stored securely and never shared. You can update them anytime in Settings.
                            </p>
                        </div>
                    </div>
                );

            case 4:
                return (
                    <div className="space-y-6 max-w-2xl mx-auto">
                        <div className="text-center mb-8">
                            <h2 className="text-3xl font-bold text-white mb-2">Let's Try It Out!</h2>
                            <p className="text-gray-400">Run a demo analysis to see Allogator in action</p>
                        </div>

                        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Sample Log File</h3>
                            <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300 overflow-x-auto">
                                <div className="space-y-1">
                                    <div className="text-red-400">[2024-01-20 14:25:12] ERROR: Database connection failed - timeout after 30s</div>
                                    <div className="text-yellow-400">[2024-01-20 14:25:13] WARN: Retrying connection (attempt 1/3)</div>
                                    <div className="text-red-400">[2024-01-20 14:25:43] ERROR: Connection retry failed</div>
                                    <div className="text-gray-400">[2024-01-20 14:25:44] INFO: Falling back to read replica</div>
                                    <div className="text-green-400">[2024-01-20 14:25:45] SUCCESS: Connected to read replica</div>
                                    <div className="text-yellow-400">[2024-01-20 14:25:46] WARN: Operating in degraded mode</div>
                                </div>
                            </div>
                        </div>

                        {!isAnalyzing && !analysisComplete && (
                            <div className="text-center">
                                <button
                                    onClick={runDemoAnalysis}
                                    className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                                >
                                    <SparklesIcon className="w-5 h-5 mr-2" />
                                    Analyze Sample Log
                                </button>
                            </div>
                        )}

                        {isAnalyzing && (
                            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
                                <div className="flex items-center justify-center space-x-3 mb-4">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-400"></div>
                                    <span className="text-gray-300">Analyzing logs...</span>
                                </div>
                                <div className="w-full bg-gray-700 rounded-full h-2">
                                    <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                                </div>
                            </div>
                        )}

                        {analysisComplete && (
                            <div className="space-y-4">
                                <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
                                    <h4 className="text-lg font-semibold text-white mb-3 flex items-center">
                                        <CheckIcon className="w-5 h-5 text-green-400 mr-2" />
                                        Analysis Complete!
                                    </h4>
                                    
                                    <div className="space-y-3">
                                        <div className="flex items-start">
                                            <span className="text-red-400 font-semibold mr-2">Critical:</span>
                                            <span className="text-gray-300">Database connection timeout detected</span>
                                        </div>
                                        
                                        <div className="flex items-start">
                                            <span className="text-yellow-400 font-semibold mr-2">Warning:</span>
                                            <span className="text-gray-300">System operating in degraded mode</span>
                                        </div>
                                        
                                        <div className="mt-4 pt-4 border-t border-gray-700">
                                            <p className="text-sm text-gray-400 mb-2">Recommended Actions:</p>
                                            <ul className="space-y-1 text-sm text-gray-300">
                                                <li>• Check database server health and network connectivity</li>
                                                <li>• Increase connection timeout to 60s for high-latency environments</li>
                                                <li>• Implement connection pooling to reduce connection overhead</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
                                    <p className="text-sm text-green-300">
                                        <strong>Great job!</strong> You've successfully run your first analysis. Allogator identified the issues and provided actionable recommendations.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                );

            case 5:
                return (
                    <div className="text-center space-y-6 max-w-md mx-auto">
                        <div className="inline-flex p-4 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 mb-4">
                            <CheckIcon className="w-16 h-16 text-green-400" />
                        </div>
                        
                        <h2 className="text-3xl font-bold text-white">You're All Set!</h2>
                        <p className="text-xl text-gray-400">
                            Welcome to Allogator, {formData.fullName.split(' ')[0]}! Your account is ready and configured.
                        </p>
                        
                        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6 text-left">
                            <h3 className="text-lg font-semibold text-white mb-4">Quick Start Tips:</h3>
                            <ul className="space-y-3">
                                <li className="flex items-start">
                                    <span className="text-green-400 mr-2">•</span>
                                    <span className="text-gray-300">Upload logs directly or paste them into the analyzer</span>
                                </li>
                                <li className="flex items-start">
                                    <span className="text-green-400 mr-2">•</span>
                                    <span className="text-gray-300">Use Ctrl+Enter for quick analysis</span>
                                </li>
                                <li className="flex items-start">
                                    <span className="text-green-400 mr-2">•</span>
                                    <span className="text-gray-300">Check the History tab to review past analyses</span>
                                </li>
                                <li className="flex items-start">
                                    <span className="text-green-400 mr-2">•</span>
                                    <span className="text-gray-300">Configure applications for automated monitoring</span>
                                </li>
                            </ul>
                        </div>

                        <button
                            onClick={completeOnboarding}
                            className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-xl hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                        >
                            Go to Dashboard
                            <ArrowRightIcon className="w-5 h-5 ml-2" />
                        </button>
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
            {/* Progress Bar */}
            <div className="w-full bg-gray-900 border-b border-gray-800">
                <div className="max-w-4xl mx-auto px-4 py-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                            <AllogatorLogo className="h-8 w-8 text-green-400" />
                            <span className="text-xl font-bold text-white">Allogator Setup</span>
                        </div>
                        <button
                            onClick={() => navigate('/')}
                            className="text-gray-400 hover:text-white transition-colors text-sm"
                        >
                            Exit Setup
                        </button>
                    </div>
                    
                    {/* Step Indicators */}
                    <div className="flex items-center justify-between">
                        {steps.map((step, index) => (
                            <div key={step.number} className="flex items-center">
                                <div className="flex flex-col items-center">
                                    <div
                                        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                                            currentStep > step.number
                                                ? 'bg-green-500 text-white'
                                                : currentStep === step.number
                                                ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white'
                                                : 'bg-gray-800 text-gray-500'
                                        }`}
                                    >
                                        {currentStep > step.number ? (
                                            <CheckIcon className="w-5 h-5" />
                                        ) : (
                                            <span className="text-sm font-semibold">{step.number}</span>
                                        )}
                                    </div>
                                    <span className={`text-xs mt-2 ${
                                        currentStep >= step.number ? 'text-gray-300' : 'text-gray-600'
                                    }`}>
                                        {step.title}
                                    </span>
                                </div>
                                {index < steps.length - 1 && (
                                    <div
                                        className={`w-full h-0.5 mx-2 transition-all ${
                                            currentStep > step.number ? 'bg-green-500' : 'bg-gray-800'
                                        }`}
                                    />
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-grow flex items-center justify-center px-4 py-12">
                <div className="w-full max-w-4xl">
                    {renderStepContent()}
                </div>
            </div>

            {/* Navigation Buttons */}
            <div className="border-t border-gray-800 bg-gray-900/50 backdrop-blur-sm">
                <div className="max-w-4xl mx-auto px-4 py-6">
                    <div className="flex justify-between items-center">
                        <button
                            onClick={handlePrevious}
                            disabled={currentStep === 1}
                            className={`flex items-center px-6 py-3 rounded-lg font-medium transition-all ${
                                currentStep === 1
                                    ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white'
                            }`}
                        >
                            <ArrowLeftIcon className="w-5 h-5 mr-2" />
                            Previous
                        </button>

                        {currentStep < totalSteps ? (
                            <button
                                onClick={handleNext}
                                disabled={(currentStep === 4 && !analysisComplete) || isCreatingAccount}
                                className={`flex items-center px-6 py-3 rounded-lg font-medium transition-all ${
                                    (currentStep === 4 && !analysisComplete) || isCreatingAccount
                                        ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                                        : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600 transform hover:scale-105'
                                }`}
                            >
                                {isCreatingAccount ? (
                                    <>
                                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                                        Creating Account...
                                    </>
                                ) : (
                                    <>
                                        Next
                                        <ArrowRightIcon className="w-5 h-5 ml-2" />
                                    </>
                                )}
                            </button>
                        ) : (
                            <button
                                onClick={completeOnboarding}
                                className="flex items-center px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all transform hover:scale-105"
                            >
                                Complete Setup
                                <CheckIcon className="w-5 h-5 ml-2" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}