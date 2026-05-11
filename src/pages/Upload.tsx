// @ts-nocheck
import React, { useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Upload, FileSpreadsheet, Loader2, X, ArrowLeft, CheckCircle, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard, DashboardData } from '@/contexts/DashboardContext';
import { api, streamDashboard, DashboardStreamEvent } from '@/services/api';
import { ProcessingProgress } from '@/components/ProcessingProgress';
import { DocumentHistory } from '@/components/DocumentHistory';
import { BackendStatusBanner } from '@/components/BackendStatusBanner';
import { useHealthCheck } from '@/hooks/useHealthCheck';

/**
 * Flatten a nested dashboard response into a single-level object.
 * 
 * The backend generate endpoint returns:
 *   { meta, dashboard: { title, kpis, charts, ... }, ceo_view, manager_view, ... }
 * 
 * The frontend DashboardRenderer expects a flat:
 *   { title, kpis, charts, meta, ceo_view, manager_view, ... }
 * 
 * This mirrors the flattening done by the backend's get_latest_dashboard_v2.
 */
function flattenDashboardPayload(raw: any): any {
    if (!raw || typeof raw !== 'object') return raw;
    
    let result: any;
    
    // If the response itself has an inner "dashboard" key, flatten
    const inner = raw.dashboard;
    if (inner && typeof inner === 'object' && !Array.isArray(inner)) {
        // Start with the inner dashboard (title, kpis, charts, sections, etc.)
        result = { ...inner };
        // Merge outer-level fields (meta, ceo_view, manager_view, etc.)
        for (const key of Object.keys(raw)) {
            if (key !== 'dashboard' && !(key in result)) {
                result[key] = raw[key];
            }
        }
    } else {
        // Already flat (has kpis/charts at top level)
        result = { ...raw };
    }
    
    // If kpis is empty but kpi_dashboard has items, populate kpis from intelligence layer
    if ((!result.kpis || result.kpis.length === 0) && Array.isArray(result.kpi_dashboard) && result.kpi_dashboard.length > 0) {
        result.kpis = result.kpi_dashboard.map((item: any, idx: number) => ({
            id: `intel_${idx}`,
            title: item.name || item.title || item.metric || 'KPI',
            value: item.current || item.value || 0,
            unit: '',
            change: item.status || 'neutral',
            changeType: (item.status === 'on_track' || item.status === 'good') ? 'positive' 
                       : (item.status === 'at_risk' || item.status === 'critical') ? 'negative' 
                       : 'neutral',
            icon: 'activity',
            color: 'cyan',
            target: item.target,
        }));
    }
    
    return result;
}

const UploadPage = () => {
    const [isDragOver, setIsDragOver] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<'gemini' | 'openai'>('gemini');
    const [enableDeduction, setEnableDeduction] = useState(true);
    const [enablePatterns, setEnablePatterns] = useState(true);
    const [showProgress, setShowProgress] = useState(false);
    const [streamStage, setStreamStage] = useState<string | null>(null);
    const streamCloseRef = useRef<(() => void) | null>(null);
    const { toast } = useToast();
    const { user, isAuthenticated, token } = useAuth();
    const navigate = useNavigate();
    const {
        dashboardData,
        setDashboardData,
        files,
        setFiles,
        isLoading,
        setIsLoading,
        docId,
        taskId,
        setDocId,
        setTaskId,
        progress,
        setProgress,
        projectMeta,
        setProjectMeta,
    } = useDashboard();

    const handleFileChange = (selectedFiles: File[]) => {
        const MAX_FILES = 20;
        const validFiles = selectedFiles.filter(file =>
            file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
            file.type === 'application/vnd.ms-excel' ||
            file.type === 'application/pdf' ||
            file.type === 'text/csv'
        );

        if (validFiles.length === 0) {
            toast({
                title: "Invalid file type",
                description: "Please upload Excel, PDF, or CSV files",
                variant: "destructive",
            });
            return;
        }

        if (validFiles.length !== selectedFiles.length) {
            toast({
                title: "Some files skipped",
                description: `${validFiles.length} of ${selectedFiles.length} files are valid. Invalid files were skipped.`,
                variant: "destructive",
            });
        }

        // Merge with already-selected files, capped at MAX_FILES
        const combined = [...files, ...validFiles];
        const capped = combined.slice(0, MAX_FILES);
        if (combined.length > MAX_FILES) {
            toast({
                title: "File limit reached",
                description: `Only the first ${MAX_FILES} files are included. Remove files to add others.`,
                variant: "destructive",
            });
        }
        setFiles(capped);
    };

    const handleRemoveFile = (indexToRemove: number) => {
        setFiles(files.filter((_, index) => index !== indexToRemove));
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        const droppedFiles = Array.from(e.dataTransfer.files);
        if (droppedFiles.length > 0) {
            handleFileChange(droppedFiles);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    };

    const handleUpload = async () => {
        if (files.length === 0) {
            toast({
                title: "No files selected",
                description: "Please select files to upload",
                variant: "destructive",
            });
            return;
        }

        setIsLoading(true);
        try {
            // Route: 1 file → single, 2-5 → batch, 6-20 → project
            const opts = {
                provider: selectedProvider,
                enable_deduction: enableDeduction,
                enable_patterns: enablePatterns,
            };
            const response = files.length === 1
                ? await api.uploadDocument(files[0], opts)
                : files.length <= 5
                    ? await api.uploadDocuments(files, opts)
                    : await api.uploadProject(files, opts);
            
            // Check if dashboard data is included in the response (synchronous processing)
            if (response.status === 'completed' && response.dashboard) {
                // Flatten the nested { meta, dashboard: { kpis, charts }, ceo_view, ... } structure
                const flatDashboard = flattenDashboardPayload(response.dashboard);
                const dashboardData: DashboardData = { dashboard: flatDashboard };
                setDashboardData(dashboardData);

                // Store project meta (clear for single-doc, set for multi)
                if ((response.files_processed ?? 1) > 1) {
                    setProjectMeta({
                        filesProcessed: response.files_processed ?? files.length,
                        batchesProcessed: (response as any).batches_processed ?? Math.ceil(files.length / 5),
                        message: response.message,
                        documents: (response as any).documents ?? [],
                        fileNames: files.map(f => f.name),
                    });
                } else {
                    setProjectMeta(null);
                }

                setIsLoading(false);
                
                toast({
                    title: "Upload successful!",
                    description: "Your dashboard is ready.",
                });
                
                // Navigate to dashboard immediately
                navigate('/dashboard');
            } else {
                // Async processing - show progress tracker
                setDocId(response.doc_id);
                setTaskId(response.task_id);
                setShowProgress(true);
                
                toast({
                    title: "Upload successful!",
                    description: "Document is being processed. You'll be notified when complete.",
                });
            }
        } catch (error: any) {
            const status = error.response?.status;
            const detail = error.response?.data?.detail || "";
            let description = "There was an error processing your file";
            if (status === 503 || detail.toLowerCase().includes("quota")) {
                description = "Gemini API daily quota exhausted. Please wait until midnight (Pacific Time) for the quota to reset, or upgrade your API plan.";
            } else if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
                description = "Processing timed out. The document may be too large or the AI service is under heavy load. Please try again.";
            } else if (detail) {
                description = detail;
            }
            toast({
                title: "Upload failed",
                description,
                variant: "destructive",
            });
            setIsLoading(false);
        }
    };

    const handleProgressComplete = async (completedDocId: string, dashboardDataFromWS?: any) => {
        // Try SSE streaming first for progressive dashboard rendering.
        // Falls back to single REST fetch if SSE fails.
        try {
            setIsLoading(true);

            // If dashboard data already came from WebSocket, use it directly
            if (dashboardDataFromWS) {
                const flat = flattenDashboardPayload(dashboardDataFromWS?.dashboard ?? dashboardDataFromWS);
                setDashboardData({ dashboard: flat } as DashboardData);
                setShowProgress(false);
                setIsLoading(false);
                toast({ title: "Processing complete!", description: "Your dashboard is ready." });
                navigate('/dashboard');
                return;
            }

            // Attempt SSE stream — progressively populate dashboard
            let receivedComplete = false;
            const partialDashboard: Record<string, any> = {};

            const closeStream = streamDashboard(
                completedDocId,
                (event: DashboardStreamEvent) => {
                    setStreamStage(event.stage);

                    if (event.stage === 'error') {
                        // SSE error — fall back to REST below
                        return;
                    }

                    if (event.stage === 'kpis' && event.data) {
                        partialDashboard.title = event.data.title;
                        partialDashboard.description = event.data.description;
                        partialDashboard.kpis = event.data.kpis;
                        // Set partial dashboard immediately so KPIs render
                        setDashboardData({ dashboard: { ...partialDashboard } } as DashboardData);
                    }

                    if (event.stage === 'charts' && event.data) {
                        partialDashboard.charts = event.data.charts;
                        partialDashboard.tables = event.data.tables;
                        setDashboardData({ dashboard: { ...partialDashboard } } as DashboardData);
                    }

                    if (event.stage === 'insights' && event.data) {
                        partialDashboard.insights = event.data.insights;
                        partialDashboard.optimizationSuggestions = event.data.optimizationSuggestions;
                        setDashboardData({ dashboard: { ...partialDashboard } } as DashboardData);
                    }

                    if (event.stage === 'sixSigma' && event.data) {
                        partialDashboard.sixSigma = event.data.sixSigma;
                        setDashboardData({ dashboard: { ...partialDashboard } } as DashboardData);
                    }

                    if (event.stage === 'complete' && event.data) {
                        receivedComplete = true;
                        const flat = flattenDashboardPayload(event.data.dashboard);
                        setDashboardData({ dashboard: flat } as DashboardData);
                        setShowProgress(false);
                        setIsLoading(false);
                        setStreamStage(null);
                        toast({ title: "Dashboard ready!", description: "All sections loaded." });
                        navigate('/dashboard');
                    }
                },
                () => {
                    // SSE error handler — fall back to REST fetch
                    if (!receivedComplete) {
                        handleFallbackFetch(completedDocId);
                    }
                },
            );

            streamCloseRef.current = closeStream;

            // Safety timeout: if SSE doesn't complete within 70s, fall back
            setTimeout(() => {
                if (!receivedComplete) {
                    closeStream();
                    handleFallbackFetch(completedDocId);
                }
            }, 70_000);

        } catch (error: any) {
            console.error('Error in handleProgressComplete:', error);
            handleFallbackFetch(completedDocId);
        }
    };

    const handleFallbackFetch = async (completedDocId: string) => {
        // REST fallback when SSE is unavailable
        try {
            const data = await api.getDashboardData(completedDocId);
            const flat = flattenDashboardPayload(data);
            setDashboardData({ dashboard: flat } as DashboardData);
        } catch (fetchError: any) {
            console.error('Fallback fetch error:', fetchError);
        }
        setShowProgress(false);
        setIsLoading(false);
        setStreamStage(null);
        toast({ title: "Processing complete!", description: "Your dashboard is ready." });
        navigate('/dashboard');
    };

    const handleProgressError = (error: string) => {
        toast({
            title: "Processing failed",
            description: error,
            variant: "destructive",
        });
        setShowProgress(false);
        setIsLoading(false);
        setDocId(null);
        setTaskId(null);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <Link to="/" className="flex items-center text-cyan-400 hover:text-cyan-300 transition-colors">
                        <ArrowLeft className="h-5 w-5 mr-2" />
                        <span className="text-sm font-medium">Back</span>
                    </Link>
                    <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center">
                            <BarChart3 className="h-4 w-4 text-white" />
                        </div>
                        <span className="text-xl font-bold text-white">TransIQ</span>
                        <Link
                          to="/confusion-matrix"
                          className="ml-4 flex items-center gap-1.5 text-sm text-slate-400 hover:text-violet-300 transition-colors border border-slate-600 hover:border-violet-500/50 rounded-lg px-3 py-1"
                        >
                          <BarChart3 className="h-3.5 w-3.5" />
                          Confusion Matrix
                        </Link>
                    </div>
                </div>

                {/* Main Content */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column - Upload Section */}
                    <div className="lg:col-span-2">
                        <div className="mb-6">
                            <h1 className="text-3xl font-bold text-white mb-2">Upload Data</h1>
                            <p className="text-slate-400">Upload your Excel or PDF files to create stunning dashboards</p>
                        </div>

                        <div className="mb-4">
                            <BackendStatusBanner />
                        </div>

                        {/* Upload Card */}
                        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                            <CardContent className="p-8">
                                <div
                                    className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${isDragOver
                                        ? 'border-cyan-400 bg-cyan-500/10'
                                        : 'border-slate-600 hover:border-cyan-400 hover:bg-slate-700/30'
                                        }`}
                                    onDrop={handleDrop}
                                    onDragOver={handleDragOver}
                                    onDragLeave={handleDragLeave}
                                >
                                    <div className="w-16 h-16 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-2xl flex items-center justify-center mx-auto mb-6">
                                        <Upload className="h-8 w-8 text-white" />
                                    </div>
                                    <h3 className="text-2xl font-semibold text-white mb-3">Upload Your Data Files</h3>
                                    <p className="text-slate-400 mb-6">
                                        Upload up to <strong className="text-cyan-400">20 files</strong> &mdash; the system auto-batches large projects and synthesises one unified master dashboard
                                    </p>

                                    <Button
                                        onClick={() => document.getElementById('file-upload')?.click()}
                                        className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-8 py-3 rounded-lg font-medium"
                                    >
                                        Choose Files
                                    </Button>

                                    <input
                                        id="file-upload"
                                        type="file"
                                        className="hidden"
                                        multiple
                                        accept=".xlsx,.xls,.pdf,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/pdf,text/csv"
                                        onChange={(e) => e.target.files && handleFileChange(Array.from(e.target.files))}
                                    />

                                    <p className="text-sm text-slate-500 mt-4">
                                        Supports .xlsx, .xls, .pdf, .csv &mdash; up to 20 files &bull; 25 MB each &bull; 1000+ pages
                                    </p>
                                </div>

                                {/* File List */}
                                {files.length > 0 && (
                                    <div className="mt-6 space-y-3">
                                        {/* Mode indicator */}
                                        {files.length > 1 && (
                                            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg mb-1 ${
                                                files.length > 5
                                                    ? 'bg-purple-500/10 border border-purple-500/30'
                                                    : 'bg-cyan-500/10 border border-cyan-500/30'
                                            }`}>
                                                <Badge className={`text-xs ${
                                                    files.length > 5
                                                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                                                        : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                                                }`}>
                                                    {files.length > 5 ? `Project Mode — ${files.length} Documents` : `${files.length} Documents`}
                                                </Badge>
                                                <span className={`text-xs ${
                                                    files.length > 5 ? 'text-purple-300' : 'text-cyan-300'
                                                }`}>
                                                    {files.length > 5
                                                        ? `Auto-batched into ${Math.ceil(files.length / 5)} groups of 5 — results synthesised into one master dashboard`
                                                        : 'Multi-document analysis — all files synthesised into one dashboard'
                                                    }
                                                </span>
                                            </div>
                                        )}
                                        {files.map((file, index) => (
                                            <div key={index} className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                                                <div className="flex items-center space-x-3">
                                                    <FileSpreadsheet className="h-5 w-5 text-cyan-400" />
                                                    <div>
                                                        <p className="text-white font-medium">{file.name}</p>
                                                        <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                                    </div>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleRemoveFile(index)}
                                                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Processing Options */}
                                {files.length > 0 && !showProgress && (
                                    <div className="mt-6 space-y-4 p-4 bg-slate-700/30 rounded-lg border border-slate-600">
                                        <h4 className="text-white font-medium mb-3">Processing Options</h4>
                                        
                                        {/* Provider Selection */}
                                        <div className="space-y-2">
                                            <Label htmlFor="provider" className="text-slate-300">AI Provider</Label>
                                            <Select value={selectedProvider} onValueChange={(value: 'gemini' | 'openai') => setSelectedProvider(value)}>
                                                <SelectTrigger id="provider" className="bg-slate-800 border-slate-600 text-white">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="gemini">Google Gemini</SelectItem>
                                                    <SelectItem value="openai">OpenAI</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        {/* Feature Flags */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between">
                                                <Label htmlFor="deduction" className="text-slate-300 cursor-pointer">
                                                    Enable Fact Extraction
                                                </Label>
                                                <Switch
                                                    id="deduction"
                                                    checked={enableDeduction}
                                                    onCheckedChange={setEnableDeduction}
                                                />
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <Label htmlFor="patterns" className="text-slate-300 cursor-pointer">
                                                    Enable Pattern Analysis
                                                </Label>
                                                <Switch
                                                    id="patterns"
                                                    checked={enablePatterns}
                                                    onCheckedChange={setEnablePatterns}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Progress Component */}
                                {showProgress && taskId && docId && (
                                    <div className="mt-6">
                                        <ProcessingProgress
                                            taskId={taskId}
                                            docId={docId}
                                            onComplete={handleProgressComplete}
                                            onError={handleProgressError}
                                        />
                                        {streamStage && (
                                            <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-cyan-500/10 rounded-lg border border-cyan-500/30">
                                                <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
                                                <span className="text-sm text-cyan-300">
                                                    {streamStage === 'context_ready' && 'Preparing context...'}
                                                    {streamStage === 'kpis' && 'KPIs loaded — rendering...'}
                                                    {streamStage === 'charts' && 'Charts loaded — rendering...'}
                                                    {streamStage === 'insights' && 'Insights loaded — rendering...'}
                                                    {streamStage === 'sixSigma' && 'Six Sigma analysis loaded...'}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Upload Button */}
                                {files.length > 0 && (
                                    <div className="mt-6 flex justify-center">
                                        <Button
                                            onClick={handleUpload}
                                            disabled={isLoading || isBackendCritical}
                                            title={isBackendCritical ? 'Processing backend is offline' : undefined}
                                            className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-8 py-3 rounded-lg font-medium"
                                        >
                                            {isLoading ? (
                                                <>
                                                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                                                    Processing...
                                                </>
                                            ) : (
                                                <>
                                                    <Upload className="h-5 w-5 mr-2" />
                                                    {files.length > 5
                                                        ? `Analyse Project (${files.length} docs)`
                                                        : files.length > 1
                                                            ? `Analyse ${files.length} Documents`
                                                            : 'Generate Dashboard'
                                                    }
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right Column - Info Cards */}
                    <div className="space-y-6">
                        {/* What happens next */}
                        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                            <CardHeader>
                                <CardTitle className="text-white text-lg">What happens next?</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-start space-x-3">
                                    <div className="w-6 h-6 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                                        <span className="text-white text-sm font-bold">1</span>
                                    </div>
                                    <div>
                                        <p className="text-white font-medium">Data Analysis</p>
                                        <p className="text-sm text-slate-400">AI reads and indexes every page of your file(s)</p>
                                    </div>
                                </div>
                                <div className="flex items-start space-x-3">
                                    <div className="w-6 h-6 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                                        <span className="text-white text-sm font-bold">2</span>
                                    </div>
                                    <div>
                                        <p className="text-white font-medium">Dashboard Creation</p>
                                        <p className="text-sm text-slate-400">Unified charts and KPIs built across all documents</p>
                                    </div>
                                </div>
                                <div className="flex items-start space-x-3">
                                    <div className="w-6 h-6 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                                        <span className="text-white text-sm font-bold">3</span>
                                    </div>
                                    <div>
                                        <p className="text-white font-medium">Insights Generation</p>
                                        <p className="text-sm text-slate-400">Cross-document patterns, DMAIC report, quality score &amp; project synthesis</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Supported Formats */}
                        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                            <CardHeader>
                                <CardTitle className="text-white text-lg">Supported Formats</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="flex items-center space-x-3">
                                    <Badge variant="secondary" className="bg-green-500/20 text-green-400 border-green-500/50">
                                        XLS
                                    </Badge>
                                    <span className="text-slate-300">Excel Spreadsheets</span>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/50">
                                        PDF
                                    </Badge>
                                    <span className="text-slate-300">PDF Documents</span>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <Badge variant="secondary" className="bg-purple-500/20 text-purple-400 border-purple-500/50">
                                        CSV
                                    </Badge>
                                    <span className="text-slate-300">Comma Separated Values</span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Document History */}
                        <DocumentHistory />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UploadPage;