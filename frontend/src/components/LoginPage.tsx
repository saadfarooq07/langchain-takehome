import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google';

// --- SVG Icons ---
const AllogatorLogo = ({ className }: { className?: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M16.596 4.5H7.404L3 12l4.404 7.5h9.192L21 12l-4.404-7.5zM15.07 16.5H8.93l-3.536-6 3.536-6h6.14l3.536 6-3.536 6z" />
        <path d="M13.895 8.25h-3.79l-1.5 2.598 1.5 2.598h3.79l1.5-2.598-1.5-2.598z" />
    </svg>
);

const ArrowLeftIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="19" y1="12" x2="5" y2="12"></line>
        <polyline points="12 19 5 12 12 5"></polyline>
    </svg>
);

export default function LoginPage() {
    const navigate = useNavigate();
    // Use environment variable or fallback to the actual client ID
    const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '872135203640-42nj7cv9mb7464hr53nhfmk6lfkv3a9j.apps.googleusercontent.com';
    
    // Debug log
    console.log('Google Client ID:', googleClientId);
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        tenantSlug: ''
    });
    const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});
    const [isLoading, setIsLoading] = useState(false);

    const handleInputChange = (field: string, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field as keyof typeof errors]) {
            setErrors(prev => ({ ...prev, [field]: undefined }));
        }
    };

    const validateForm = (): boolean => {
        const newErrors: typeof errors = {};

        if (!formData.email.trim()) {
            newErrors.email = 'Email is required';
        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
            newErrors.email = 'Invalid email format';
        }

        if (!formData.password.trim()) {
            newErrors.password = 'Password is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!validateForm()) return;

        setIsLoading(true);
        setErrors({});

        try {
            await authService.login(
                formData.email, 
                formData.password, 
                formData.tenantSlug || undefined
            );
            
            // Redirect to app after successful login
            navigate('/app');
        } catch (error: any) {
            setErrors({ 
                general: error.response?.data?.detail || error.message || 'Invalid email or password' 
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleSuccess = async (credentialResponse: any) => {
        setIsLoading(true);
        setErrors({});

        try {
            // Call backend OAuth endpoint
            await authService.googleAuth(credentialResponse.credential);
            
            // Redirect to app
            navigate('/app');
        } catch (error: any) {
            setErrors({ 
                general: error.response?.data?.detail || 'Failed to sign in with Google. Please try again.' 
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleError = () => {
        setErrors({ general: 'Google sign-in failed. Please try again.' });
    };

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-4">
            {/* Background gradient */}
            <div className="fixed inset-0 opacity-30">
                <div className="absolute inset-0 bg-gradient-to-br from-green-900/20 via-transparent to-purple-900/20" />
            </div>

            <div className="relative z-10 w-full max-w-md">
                {/* Logo and title */}
                <div className="text-center mb-8">
                    <Link to="/" className="inline-flex items-center justify-center mb-6">
                        <AllogatorLogo className="h-12 w-12 text-green-400" />
                    </Link>
                    <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
                    <p className="text-gray-400">Sign in to your Allogator account</p>
                </div>

                {/* Login form */}
                <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-8">
                    {errors.general && (
                        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6">
                            <p className="text-sm text-red-400">{errors.general}</p>
                        </div>
                    )}

                    {/* Google OAuth Button */}
                    <GoogleOAuthProvider clientId={googleClientId}>
                        <div className="mb-6">
                            <GoogleLogin
                                onSuccess={handleGoogleSuccess}
                                onError={handleGoogleError}
                                useOneTap
                                theme="filled_black"
                                size="large"
                                width="100%"
                                text="signin_with"
                                shape="rectangular"
                            />
                        </div>
                    </GoogleOAuthProvider>

                    {/* Divider */}
                    <div className="relative mb-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-700"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-4 bg-gray-900/50 text-gray-400">Or sign in with email</span>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">

                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                Email Address
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
                                autoComplete="email"
                                autoFocus
                            />
                            {errors.email && (
                                <p className="mt-1 text-sm text-red-400">{errors.email}</p>
                            )}
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                                Password
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
                                autoComplete="current-password"
                            />
                            {errors.password && (
                                <p className="mt-1 text-sm text-red-400">{errors.password}</p>
                            )}
                        </div>

                        <div>
                            <label htmlFor="tenantSlug" className="block text-sm font-medium text-gray-300 mb-2">
                                Workspace (Optional)
                            </label>
                            <input
                                type="text"
                                id="tenantSlug"
                                value={formData.tenantSlug}
                                onChange={(e) => handleInputChange('tenantSlug', e.target.value)}
                                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all"
                                placeholder="my-workspace"
                            />
                            <p className="mt-1 text-xs text-gray-500">
                                Leave empty to use your default workspace
                            </p>
                        </div>

                        <div className="flex items-center justify-between">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    className="w-4 h-4 bg-gray-800 border-gray-700 rounded text-green-500 focus:ring-green-500"
                                />
                                <span className="ml-2 text-sm text-gray-300">Remember me</span>
                            </label>
                            <a href="#" className="text-sm text-green-400 hover:text-green-300 transition-colors">
                                Forgot password?
                            </a>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className={`w-full py-3 px-4 rounded-lg font-medium transition-all ${
                                isLoading
                                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600 transform hover:scale-[1.02]'
                            }`}
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                                    Signing in...
                                </span>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-sm text-gray-400">
                            Don't have an account?{' '}
                            <Link to="/signup" className="text-green-400 hover:text-green-300 transition-colors font-medium">
                                Get started free
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Back to home */}
                <div className="mt-8 text-center">
                    <Link to="/" className="inline-flex items-center text-sm text-gray-400 hover:text-white transition-colors">
                        <ArrowLeftIcon className="w-4 h-4 mr-2" />
                        Back to home
                    </Link>
                </div>
            </div>
        </div>
    );
}