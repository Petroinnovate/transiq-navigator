import React, { useEffect, useRef } from 'react';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { api } from '@/services/api';

interface ProcessingProgressProps {
  taskId: string;
  docId: string;
  onComplete: (docId: string, dashboardData?: any) => void;
  onError: (error: string) => void;
}

// Step sequence: maps attempt count ranges to step names + fake progress ceilings
const STEPS = [
  { until: 2,  step: 'initializing',       ceil: 10 },
  { until: 5,  step: 'reading',            ceil: 25 },
  { until: 10, step: 'chunking',           ceil: 45 },
  { until: 18, step: 'embedding',          ceil: 70 },
  { until: 28, step: 'generating_insights',ceil: 88 },
  { until: 50, step: 'ai_writing',         ceil: 94 },
  { until: Infinity, step: 'finalizing',    ceil: 97 },
];

export const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  taskId,
  docId,
  onComplete,
  onError,
}) => {
  const [progress, setProgress] = React.useState(0);
  const [currentStep, setCurrentStep] = React.useState('initializing');
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const attemptCountRef = useRef(0);

  useEffect(() => {
    let mounted = true;

    const checkProcessingStatus = async () => {
      try {
        attemptCountRef.current += 1;
        const n = attemptCountRef.current;
        
        // Check task status first — this is the authoritative source
        let taskCompleted = false;
        let taskFailed = false;
        let taskError = '';
        let taskProgress = 0;
        let taskStage = '';
        try {
          const taskStatus = await api.getTaskStatus(taskId);
          if (taskStatus.status === 'completed') {
            taskCompleted = true;
          } else if (taskStatus.status === 'failed') {
            taskFailed = true;
            taskError = taskStatus.error || 'Processing failed';
          }
          if (taskStatus.progress > 0) {
            taskProgress = taskStatus.progress;
            taskStage = taskStatus.stage || 'processing';
          }
        } catch {
          // Task endpoint not available — rely on dashboard endpoint below
        }

        if (!mounted) return;

        // If task failed, stop immediately
        if (taskFailed) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          onError(taskError);
          return;
        }

        // Try dashboard endpoint (returns data when processing is complete)
        const data = await api.getDashboardData(docId);

        if (!mounted) return;

        // If status is explicitly "processing", dashboard isn't ready yet
        if (data.status === 'processing') {
          // Use real progress from task status if available
          if (taskProgress > 0) {
            setProgress(Math.min(taskProgress, 97));
            setCurrentStep(taskStage || 'processing');
            return;
          }
          
          // Fake progress fallback
          const stage = STEPS.find(s => n <= s.until) ?? STEPS[STEPS.length - 1];
          const prevCeil = STEPS[Math.max(0, STEPS.indexOf(stage) - 1)]?.ceil ?? 0;
          const fraction = Math.min(1, (n - (STEPS[STEPS.indexOf(stage) - 1]?.until ?? 0)) /
                                       (stage.until - (STEPS[STEPS.indexOf(stage) - 1]?.until ?? 0)));
          const estimated = Math.round(prevCeil + fraction * (stage.ceil - prevCeil));
          setProgress(estimated);
          setCurrentStep(stage.step);
          return;
        }

        // Complete when kpis are present (or sections — some reports have sections but no kpis)
        const kpis = data.dashboard?.kpis || data.kpis;
        const sections = data.dashboard?.sections || data.sections;
        if ((kpis && kpis.length > 0) || (sections && sections.length > 0)) {
          setProgress(100);
          setCurrentStep('completed');
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          onComplete(docId, data);
          return;
        }

        // Dashboard returned but KPIs/sections empty — check if task says completed
        if (taskCompleted) {
          // Task is done; dashboard data is the final result (even if sparse)
          setProgress(100);
          setCurrentStep('completed');
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          onComplete(docId, data);
          return;
        }

        // Still processing — show fake progress
        const stage = STEPS.find(s => n <= s.until) ?? STEPS[STEPS.length - 1];
        const prevCeil = STEPS[Math.max(0, STEPS.indexOf(stage) - 1)]?.ceil ?? 0;
        const fraction = Math.min(1, (n - (STEPS[STEPS.indexOf(stage) - 1]?.until ?? 0)) /
                                     (stage.until - (STEPS[STEPS.indexOf(stage) - 1]?.until ?? 0)));
        const estimated = Math.round(prevCeil + fraction * (stage.ceil - prevCeil));
        setProgress(estimated);
        setCurrentStep(stage.step);

      } catch (error: any) {
        console.error('Polling error:', error);
        // Timeout after 15 minutes (180 × 5s) for very large PDFs
        if (attemptCountRef.current > 180) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          onError('Processing timeout — the file may be too large. Please try a smaller file.');
        }
      }
    };

    checkProcessingStatus();
    pollIntervalRef.current = setInterval(checkProcessingStatus, 5000);

    return () => {
      mounted = false;
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [docId, onComplete, onError]);

  const stepLabels: Record<string, string> = {
    initializing:        'Initializing pipeline...',
    reading:             'Reading document...',
    chunking:            'Splitting into sections...',
    embedding:           'Building semantic index...',
    generating_insights: 'Generating AI insights and KPIs...',
    ai_writing:          'AI is writing your dashboard...',
    finalizing:          'Finalizing results...',
    completed:           'Processing complete!',
  };

  const isSlowStage = currentStep === 'embedding' || currentStep === 'generating_insights' ||
                      currentStep === 'ai_writing' || currentStep === 'finalizing';

  return (
    <Card className="bg-slate-800/50 border-slate-700">
      <CardContent className="p-6">
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium">Processing Document</p>
              <p className={`text-sm mt-0.5 ${isSlowStage ? 'text-amber-400' : 'text-slate-400'}`}>
                {stepLabels[currentStep] || 'Processing...'}
              </p>
              {isSlowStage && (
                <p className="text-xs text-slate-500 mt-0.5">
                  AI generation takes 1–2 minutes — the backend is working.
                </p>
              )}
            </div>
            <span className="text-sm text-slate-400 shrink-0">{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
};

