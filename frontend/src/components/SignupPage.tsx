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

const CheckIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
);

const GoogleIcon = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
);

export default function SignupPage() {
    const navigate = useNavigate();
    // Use environment variable or fallback to the actual client ID
    const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '872135203640-42nj7cv9mb7464hr53nhfmk6lfkv3a9j.apps.googleusercontent.com';
    
    // Debug log
    console.log('Google Client ID:', googleClientId);
    const [formData, setFormData] = useState({
        fullName: '',
        email: '',
        password: '',
        company: ''
    });
    const [errors, setErrors] = useState<{ email?: string; password?: string; fullName?: string; general?: string }>({});
    const [isLoading, setIsLoading] = useState(false);

    const handleInputChange = (field: string, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field as keyof typeof errors]) {
            setErrors(prev => ({ ...prev, [field]: undefined }));
        }
    };

    const validateForm = (): boolean => {
        const newErrors: typeof errors = {};

        if (!formData.fullName.trim()) {
            newErrors.fullName = 'Name is required';
        }

        if (!formData.email.trim()) {
            newErrors.email = 'Email is required';
        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
            newErrors.email = 'Invalid email format';
        }

        if (!formData.password.trim()) {
            newErrors.password = 'Password is required';
        } else if (formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters';
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
                description: formData.company ? `Team at ${formData.company}` : 'Individual workspace'
            });
            
            // Auto-login after successful registration
            await authService.login(formData.email, formData.password, tenantSlug);
            
            // Redirect to app
            navigate('/app');
        } catch (error: any) {
            setErrors({ 
                general: error.response?.data?.detail || error.message || 'Failed to create account. Please try again.' 
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
            const response = await authService.googleAuth(credentialResponse.credential);
            
            // Store auth data
            localStorage.setItem('allogator_access_token', response.tokens.access_token);
            localStorage.setItem('allogator_refresh_token', response.tokens.refresh_token);
            localStorage.setItem('allogator_user', JSON.stringify(response.user));
            
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
                    <h1 className="text-3xl font-bold text-white mb-2">Create Your Account</h1>
                    <p className="text-gray-400">Get unlimited access during our beta</p>
                </div>

                {/* Benefits */}
                <div className="bg-gray-900/30 backdrop-blur-sm border border-gray-800 rounded-xl p-4 mb-6">
                    <div className="space-y-2">
                        <div className="flex items-center">
                            <CheckIcon className="w-4 h-4 text-green-400 mr-3 flex-shrink-0" />
                            <span className="text-sm text-gray-300">Unlimited log analyses</span>
                        </div>
                        <div className="flex items-center">
                            <CheckIcon className="w-4 h-4 text-green-400 mr-3 flex-shrink-0" />
                            <span className="text-sm text-gray-300">Save analysis history</span>
                        </div>
                        <div className="flex items-center">
                            <CheckIcon className="w-4 h-4 text-green-400 mr-3 flex-shrink-0" />
                            <span className="text-sm text-gray-300">Free during beta</span>
                        </div>
                    </div>
                </div>

                {/* Signup form */}
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
                                text="signup_with"
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
                            <span className="px-4 bg-gray-900/50 text-gray-400">Or sign up with email</span>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">

                        <div>
                            <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-2">
                                Full Name
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
                                autoComplete="name"
                                autoFocus
                            />
                            {errors.fullName && (
                                <p className="mt-1 text-sm text-red-400">{errors.fullName}</p>
                            )}
                        </div>

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
                                autoComplete="new-password"
                            />
                            {errors.password && (
                                <p className="mt-1 text-sm text-red-400">{errors.password}</p>
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
                                autoComplete="organization"
                            />
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
                                    Creating account...
                                </span>
                            ) : (
                                'Create Free Account'
                            )}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-sm text-gray-400">
                            Already have an account?{' '}
                            <Link to="/login" className="text-green-400 hover:text-green-300 transition-colors font-medium">
                                Sign in
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Back to app */}
                <div className="mt-8 text-center">
                    <Link to="/app" className="inline-flex items-center text-sm text-gray-400 hover:text-white transition-colors">
                        <ArrowLeftIcon className="w-4 h-4 mr-2" />
                        Back to app
                    </Link>
                </div>
            </div>
        </div>
    );
}