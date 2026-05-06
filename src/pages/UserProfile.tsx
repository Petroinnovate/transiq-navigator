// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, FileText, Calendar, ArrowLeft, Loader2, Home, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { DashboardData, useDashboard } from '@/contexts/DashboardContext';
import axios from '@/lib/axios';

interface UserDetails {
    user_id: string;
    email: string;
    name?: string;
    created_at?: string;
    last_login?: string;
}

interface HistoryRecord {
    id: string;
    file_names: string[];
    created_at: string;
}

interface HistoryResponse {
    records: HistoryRecord[];
    count: number;
}

const UserProfile = () => {
    const [userDetails, setUserDetails] = useState<UserDetails | null>(null);
    const [historyData, setHistoryData] = useState<HistoryResponse | null>(null);
    const [isLoadingProfile, setIsLoadingProfile] = useState(true);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true);
    const [loadingHistoryId, setLoadingHistoryId] = useState<string | null>(null);
    const { user, token, logout } = useAuth();
    const { setDashboardData } = useDashboard();
    const { toast } = useToast();
    const navigate = useNavigate();

    useEffect(() => {
        fetchUserDetails();
        fetchUploadHistory();
    }, []);

    const fetchUserDetails = async () => {
        try {
            const response = await axios.get('/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.data;
            setUserDetails(data);
        } catch (error) {
            console.error('Error fetching user details:', error);
            // Fallback to locally stored user data
            if (user) {
                setUserDetails({ user_id: user.user_id || '', email: user.email || '' });
            } else {
                toast({
                    title: "Error",
                    description: "Failed to load user details",
                    variant: "destructive",
                });
            }
        } finally {
            setIsLoadingProfile(false);
        }
    };

    const fetchUploadHistory = async () => {
        try {
            // Fallback: load history from localStorage since /history/ endpoint doesn't exist
            const stored = localStorage.getItem('transiq_upload_history');
            if (stored) {
                const records: HistoryRecord[] = JSON.parse(stored);
                setHistoryData({ records, count: records.length });
            } else {
                setHistoryData({ records: [], count: 0 });
            }
        } catch (error) {
            console.error('Error loading upload history:', error);
            setHistoryData({ records: [], count: 0 });
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getInitials = (name?: string, email?: string) => {
        if (name) {
            return name.split(' ').map(n => n[0]).join('').toUpperCase();
        }
        return email ? email[0].toUpperCase() : 'U';
    };

    const handleLogout = async () => {
        try {
            await logout();
            toast({
                title: "Logged out",
                description: "You have been successfully logged out",
            });
        } catch (error) {
            console.error('Logout error:', error);
            toast({
                title: "Logout completed",
                description: "You have been logged out (with some issues)",
            });
        }
    };

    const handleHistoryCardClick = async (historyId: string) => {
        setLoadingHistoryId(historyId);
        try {
            // Load from localStorage since backend /history/{id} doesn't exist
            const stored = localStorage.getItem('transiq_upload_history');
            const records: HistoryRecord[] = stored ? JSON.parse(stored) : [];
            const record = records.find(r => r.id === historyId);
            
            // Try loading the dashboard data from localStorage cache
            const dashboardKey = `transiq_dashboard_${historyId}`;
            const cachedDashboard = localStorage.getItem(dashboardKey);
            
            if (cachedDashboard) {
                setDashboardData(JSON.parse(cachedDashboard) as DashboardData);
                navigate('/dashboard');
                toast({
                    title: "Dashboard Loaded",
                    description: "Successfully loaded dashboard from history",
                });
            } else {
                toast({
                    title: "Not Available",
                    description: "Dashboard data is no longer cached locally",
                    variant: "destructive",
                });
            }
        } catch (error) {
            console.error('Error loading history:', error);
            toast({
                title: "Error",
                description: "Failed to load dashboard from history",
                variant: "destructive",
            });
        } finally {
            setLoadingHistoryId(null);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-2 animate-in fade-in duration-400">
            <div className="max-w-full mx-auto px-4 animate-in slide-in-from-top-4 duration-500 delay-100">
                {/* Navigation Header */}
                <div className="flex justify-between items-center mb-8 animate-in slide-in-from-top-4 duration-500 delay-200">
                    <div className="flex items-center">
                        <div className="w-8 h-8 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center mr-3 transform hover:scale-110 transition-transform duration-300">
                            <BarChart3 className="h-4 w-4 text-white" />
                        </div>
                        <span className="text-2xl font-bold text-white hover:text-cyan-300 transition-colors duration-300">
                            TransIQ
                        </span>
                    </div>
                    <div className="flex items-center space-x-4">
                        <Button
                            variant="outline"
                            onClick={handleLogout}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 transition-all duration-300 transform hover:scale-105"
                        >
                            Logout
                        </Button>
                    </div>
                </div>

                {/* Back Button */}
                <div className="mb-6 animate-in slide-in-from-left-4 duration-500 delay-300">
                    <Link to="/">
                        <Button variant="ghost" className="flex items-center space-x-2 text-cyan-400 hover:text-cyan-300 transition-all duration-300 transform hover:scale-105 hover:translate-x-1">
                            <ArrowLeft className="h-4 w-4" />
                            <span>Back to Home</span>
                        </Button>
                    </Link>
                </div>

                {/* User Profile Section */}
                <Card className="mb-8 bg-slate-800/50 border-slate-700 backdrop-blur-sm hover:bg-slate-800/70 hover:border-cyan-500/50 transition-all duration-500 transform hover:scale-[1.02] animate-in slide-in-from-bottom-4 duration-500 delay-400">
                    <CardHeader>
                        <CardTitle className="flex items-center text-2xl text-white">
                            <User className="h-6 w-6 mr-2 text-cyan-400 animate-pulse" />
                            User Profile
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoadingProfile ? (
                            <div className="flex items-center justify-center py-8 animate-in fade-in duration-700">
                                <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
                                <span className="ml-2 text-slate-300 animate-pulse">Loading profile...</span>
                            </div>
                        ) : (
                            <div className="flex items-start space-x-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                <Avatar className="h-20 w-20 transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-cyan-500/25">
                                    <AvatarImage src="" alt="Profile" />
                                    <AvatarFallback className="text-2xl bg-gradient-to-r from-cyan-400 to-teal-400 text-white">
                                        {getInitials(userDetails?.name || user?.name, userDetails?.email || user?.email)}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1">
                                    <h3 className="text-xl font-semibold text-white mb-2 hover:text-cyan-300 transition-colors duration-300">
                                        {userDetails?.name || user?.name || 'No name set'}
                                    </h3>
                                    <p className="text-slate-400 mb-4 hover:text-slate-300 transition-colors duration-300">{userDetails?.email || user?.email}</p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                        <div className="hover:bg-slate-700/50 p-2 rounded-lg transition-all duration-300">
                                            <span className="font-medium text-slate-300">User ID:</span>
                                            <span className="ml-2 text-slate-400 font-mono">{userDetails?.user_id || user?.user_id}</span>
                                        </div>
                                        {userDetails?.created_at && (
                                            <div className="hover:bg-slate-700/50 p-2 rounded-lg transition-all duration-300">
                                                <span className="font-medium text-slate-300">Member since:</span>
                                                <span className="ml-2 text-slate-400">{formatDate(userDetails.created_at)}</span>
                                            </div>
                                        )}
                                        {userDetails?.last_login && (
                                            <div className="hover:bg-slate-700/50 p-2 rounded-lg transition-all duration-300">
                                                <span className="font-medium text-slate-300">Last login:</span>
                                                <span className="ml-2 text-slate-400">{formatDate(userDetails.last_login)}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Upload History Section */}
                <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm hover:bg-slate-800/70 hover:border-cyan-500/50 transition-all duration-500 transform hover:scale-[1.01] animate-in slide-in-from-bottom-4 duration-500 delay-500">
                    <CardHeader>
                        <CardTitle className="flex items-center text-2xl text-white">
                            <FileText className="h-6 w-6 mr-2 text-cyan-400 animate-pulse" />
                            Upload History
                            {historyData && (
                                <Badge variant="secondary" className="ml-3 bg-slate-700 text-slate-300 animate-in fade-in duration-500 delay-700">
                                    {historyData.count} record{historyData.count !== 1 ? 's' : ''}
                                </Badge>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoadingHistory ? (
                            <div className="flex items-center justify-center py-8 animate-in fade-in duration-700">
                                <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
                                <span className="ml-2 text-slate-300 animate-pulse">Loading upload history...</span>
                            </div>
                        ) : !historyData || historyData.records.length === 0 ? (
                            <div className="text-center py-8 text-slate-400 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                <FileText className="h-16 w-16 mx-auto mb-4 text-slate-600 animate-bounce" />
                                <p className="text-lg">No uploads yet</p>
                                <p className="text-sm">Your upload history will appear here</p>
                            </div>
                        ) : (
                            <div className="space-y-4 max-h-96 overflow-y-auto">
                                {historyData.records.map((record, index) => (
                                    <Card
                                        key={index}
                                        className="bg-slate-700/50 border-slate-600 hover:bg-slate-700/70 hover:border-cyan-500/50 transition-all duration-300 cursor-pointer group transform hover:scale-[1.02] hover:shadow-lg hover:shadow-cyan-500/10 animate-in fade-in slide-in-from-bottom-4 duration-500"
                                        style={{ animationDelay: `${index * 100}ms` }}
                                        onClick={() => handleHistoryCardClick(record.id)}
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex items-start justify-between">
                                                <div className="flex items-start space-x-3 flex-1 min-w-0">
                                                    <FileText className="h-5 w-5 text-cyan-400 flex-shrink-0 mt-0.5 group-hover:text-cyan-300 transition-all duration-300 group-hover:scale-110" />
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center space-x-2 mb-2">
                                                            <Calendar className="h-4 w-4 text-slate-400 group-hover:text-slate-300 transition-colors duration-300" />
                                                            <span className="text-sm text-slate-300 group-hover:text-white transition-colors duration-300">
                                                                {formatDate(record.created_at)}
                                                            </span>
                                                        </div>
                                                        <div className="space-y-1">
                                                            <p className="text-sm font-medium text-white group-hover:text-cyan-300 transition-colors duration-300">
                                                                Files ({record.file_names.length}):
                                                            </p>
                                                            <div className="flex flex-wrap gap-1">
                                                                {record.file_names.slice(0, 3).map((fileName, fileIndex) => (
                                                                    <Badge
                                                                        key={fileIndex}
                                                                        variant="outline"
                                                                        className="text-xs max-w-[200px] truncate bg-slate-600/50 border-slate-500 text-slate-200 hover:bg-slate-600/70 hover:border-cyan-400/50 transition-all duration-300"
                                                                        title={fileName}
                                                                    >
                                                                        {fileName}
                                                                    </Badge>
                                                                ))}
                                                                {record.file_names.length > 3 && (
                                                                    <Badge variant="outline" className="text-xs bg-slate-600/50 border-slate-500 text-slate-200 hover:bg-slate-600/70 hover:border-cyan-400/50 transition-all duration-300">
                                                                        +{record.file_names.length - 3} more
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                            {record.file_names.length > 3 && (
                                                                <details className="mt-2" onClick={(e) => e.stopPropagation()}>
                                                                    <summary className="text-xs text-cyan-400 hover:text-cyan-300 cursor-pointer transition-colors duration-300">
                                                                        Show all files
                                                                    </summary>
                                                                    <div className="mt-1 flex flex-wrap gap-1 animate-in fade-in slide-in-from-top-2 duration-300">
                                                                        {record.file_names.slice(3).map((fileName, fileIndex) => (
                                                                            <Badge
                                                                                key={fileIndex}
                                                                                variant="outline"
                                                                                className="text-xs max-w-[200px] truncate bg-slate-600/50 border-slate-500 text-slate-200 hover:bg-slate-600/70 hover:border-cyan-400/50 transition-all duration-300"
                                                                                title={fileName}
                                                                            >
                                                                                {fileName}
                                                                            </Badge>
                                                                        ))}
                                                                    </div>
                                                                </details>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                {loadingHistoryId === record.id && (
                                                    <div className="flex items-center text-cyan-400 animate-in fade-in duration-300">
                                                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                                        <span className="text-sm animate-pulse">Loading...</span>
                                                    </div>
                                                )}
                                            </div>
                                            {loadingHistoryId !== record.id && (
                                                <div className="mt-2 text-xs text-slate-400 opacity-0 group-hover:opacity-100 transition-all duration-300 transform group-hover:translate-y-0 translate-y-1">
                                                    Click to load this dashboard
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default UserProfile;