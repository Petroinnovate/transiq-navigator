import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Upload, LogIn, RotateCcw, Eye, BarChart3, Bot, Activity, Network, Zap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger
} from '@/components/ui/alert-dialog';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard } from '@/contexts/DashboardContext';

const Index = () => {
    const { toast } = useToast();
    const { user, isAuthenticated } = useAuth();
    const {
        dashboardData,
        resetDashboard
    } = useDashboard();
    const navigate = useNavigate();

    const getInitials = (name?: string, email?: string) => {
        if (name) {
            return name.split(' ').map(n => n[0]).join('').toUpperCase();
        }
        return email ? email[0].toUpperCase() : 'U';
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Navigation Header */}
                <div className="flex justify-between items-center mb-8">
                    <div className="flex items-center">
                        <div className="flex items-center space-x-2">
                            <div className="w-8 h-8 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center">
                                <BarChart3 className="h-6 w-6 text-white" />
                            </div>
                            <span className="text-2xl font-bold text-white">TransIQ</span>
                        </div>
                    </div>
                    <div className="flex items-center space-x-4">
                        {dashboardData && (
                            <AlertDialog>
                                <AlertDialogTrigger asChild>
                                    <Button variant="outline" className="flex items-center space-x-2 bg-slate-800 border-slate-700 text-white hover:bg-slate-700">
                                        <RotateCcw className="h-4 w-4" />
                                        <span>New Visualization</span>
                                    </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent className="bg-slate-800 border-slate-700">
                                    <AlertDialogHeader>
                                        <AlertDialogTitle className="text-white">Start New Visualization?</AlertDialogTitle>
                                        <AlertDialogDescription className="text-slate-300">
                                            This will clear your current dashboard and uploaded files. Are you sure you want to continue?
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel className="bg-slate-700 border-slate-600 text-white hover:bg-slate-600">Cancel</AlertDialogCancel>
                                        <AlertDialogAction
                                            className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600"
                                            onClick={() => {
                                                resetDashboard();
                                                navigate('/upload');
                                                toast({
                                                    title: "Dashboard cleared",
                                                    description: "Ready for new visualization",
                                                });
                                            }}
                                        >
                                            Continue
                                        </AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        )}
                        {isAuthenticated ? (
                            <Link to="/profile">
                                <Button variant="outline" className="flex items-center space-x-2 bg-slate-800 border-slate-700 text-white hover:bg-slate-700">
                                    <Avatar className="h-6 w-6">
                                        <AvatarImage src="" alt="Profile" />
                                        <AvatarFallback className="text-xs bg-cyan-500 text-white">
                                            {getInitials(user?.name, user?.email)}
                                        </AvatarFallback>
                                    </Avatar>
                                    <span>Profile</span>
                                </Button>
                            </Link>
                        ) : (
                            <Link to="/auth">
                                <Button variant="outline" className="flex items-center space-x-2 bg-slate-800 border-slate-700 text-white hover:bg-slate-700">
                                    <LogIn className="h-4 w-4" />
                                    <span>Sign In</span>
                                </Button>
                            </Link>
                        )}
                    </div>
                </div>

                <div className="text-center mb-12">
                    <div className="flex items-center justify-center mb-6">
                        <div className="flex items-center space-x-3">
                            <div className="w-16 h-16 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-2xl flex items-center justify-center">
                                <BarChart3 className="h-12 w-12 text-white" />
                            </div>
                            <span className="text-3xl font-bold text-white">TransIQ</span>
                        </div>
                    </div>
                    <h1 className="text-6xl font-bold text-white mb-6">
                        Transform Data Into{' '}
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-400">
                            Actionable Insights
                        </span>
                    </h1>
                    <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-8">
                        Upload your Excel or PDF files and watch as AI transforms them into stunning, interactive dashboards with world-class analytics and intelligence.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
                        {dashboardData ? (
                            <Link to="/dashboard">
                                <Button
                                    className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-8 py-4 text-lg rounded-xl transition-all duration-300 transform hover:scale-105"
                                >
                                    <BarChart3 className="h-5 w-5 mr-2" />
                                    Go to Dashboard
                                </Button>
                            </Link>
                        ) : (
                            <Link to="/upload">
                                <Button
                                    className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-8 py-4 text-lg rounded-xl transition-all duration-300 transform hover:scale-105"
                                >
                                    <Upload className="h-5 w-5 mr-2" />
                                    Upload Your Data
                                </Button>
                            </Link>
                        )}
                        <Link to="/demo">
                            <Button
                                variant="outline"
                                className="bg-transparent border-slate-600 text-white hover:bg-slate-800 px-8 py-4 text-lg rounded-xl"
                            >
                                <Eye className="h-5 w-5 mr-2" />
                                View Demo Dashboard
                            </Button>
                        </Link>
                        <Link to="/agent-lab">
                            <Button
                                variant="outline"
                                className="bg-transparent border-cyan-500/60 text-cyan-200 hover:bg-cyan-500/10 px-8 py-4 text-lg rounded-xl"
                            >
                                <Bot className="h-5 w-5 mr-2" />
                                Open Agent Lab
                            </Button>
                        </Link>
                    </div>

                    {/* Platform tools row */}
                    <div className="flex flex-col sm:flex-row gap-3 justify-center mb-12">
                        <Link to="/observability">
                            <Button variant="outline" className="bg-transparent border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 px-6 py-3 rounded-xl">
                                <Activity className="h-4 w-4 mr-2" /> Observability
                            </Button>
                        </Link>
                        <Link to="/intelligence">
                            <Button variant="outline" className="bg-transparent border-violet-500/40 text-violet-300 hover:bg-violet-500/10 px-6 py-3 rounded-xl">
                                <Zap className="h-4 w-4 mr-2" /> Intelligence Hub
                            </Button>
                        </Link>
                        <Link to="/graph-explorer">
                            <Button variant="outline" className="bg-transparent border-amber-500/40 text-amber-300 hover:bg-amber-500/10 px-6 py-3 rounded-xl">
                                <Network className="h-4 w-4 mr-2" /> Knowledge Graph
                            </Button>
                        </Link>
                    </div>

                    {/* Stats Section */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto mb-16">
                        <div className="text-center">
                            <div className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-400 mb-2">
                                10M+
                            </div>
                            <div className="text-slate-300">Data Points Analyzed</div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-400 mb-2">
                                94%
                            </div>
                            <div className="text-slate-300">Accuracy Rate</div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-400 mb-2">
                                &lt;30s
                            </div>
                            <div className="text-slate-300">Dashboard Generation</div>
                        </div>
                    </div>
                </div>
                <>
                    {/* Why Choose TransIQ Section */}
                    <div className="mb-16">
                        <h2 className="text-3xl font-bold text-white text-center mb-4">Why Choose TransIQ?</h2>
                        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
                            Built for modern businesses that need fast, accurate, and beautiful data insights
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            <Card className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group">
                                <CardContent className="p-6">
                                    <div className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <Upload className="h-6 w-6 text-white" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Drag & Drop Upload</h3>
                                    <p className="text-slate-400">Simply upload your Excel, PDF, or CSV files and watch the magic happen.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group">
                                <CardContent className="p-6">
                                    <div className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <div className="w-6 h-6 bg-white rounded-sm flex items-center justify-center">
                                            <div className="w-3 h-3 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-sm"></div>
                                        </div>
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">AI-Powered Insights</h3>
                                    <p className="text-slate-400">Advanced AI analyzes your data to surface hidden patterns and opportunities.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group">
                                <CardContent className="p-6">
                                    <div className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <div className="w-6 h-6 text-white">📊</div>
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Interactive Charts</h3>
                                    <p className="text-slate-400">Beautiful, responsive charts that let you tell your data story with clarity.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group">
                                <CardContent className="p-6">
                                    <div className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <div className="w-6 h-6 text-white">⚡</div>
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Real-time Processing</h3>
                                    <p className="text-slate-400">Lightning-fast data processing with instant dashboard generation.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group">
                                <CardContent className="p-6">
                                    <div className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <div className="w-6 h-6 text-white">🔒</div>
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Enterprise Security</h3>
                                    <p className="text-slate-400">Your data is protected with enterprise-grade security and privacy.</p>
                                </CardContent>
                            </Card>

                            <Card className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group">
                                <CardContent className="p-6">
                                    <div className="w-12 h-12 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <div className="w-6 h-6 text-white">💡</div>
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Smart Recommendations</h3>
                                    <p className="text-slate-400">Get actionable recommendations to improve your business performance.</p>
                                </CardContent>
                            </Card>
                        </div>
                    </div>

                    {/* CTA Section */}
                    <div className="text-center py-16">
                        <h2 className="text-3xl font-bold text-white mb-4">Ready to Transform Your Data?</h2>
                        <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
                            Join thousands of businesses already using TransIQ to make better decisions
                        </p>
                        {dashboardData ? (
                            <Link to="/dashboard">
                                <Button
                                    className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-8 py-4 text-lg rounded-xl transition-all duration-300 transform hover:scale-105"
                                >
                                    <BarChart3 className="h-5 w-5 mr-2" />
                                    View Your Dashboard
                                </Button>
                            </Link>
                        ) : (
                            <Link to="/upload">
                                <Button
                                    className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-8 py-4 text-lg rounded-xl transition-all duration-300 transform hover:scale-105"
                                >
                                    Get Started Now
                                </Button>
                            </Link>
                        )}
                    </div>
                </>
            </div>
        </div>
    );
};

export default Index;
