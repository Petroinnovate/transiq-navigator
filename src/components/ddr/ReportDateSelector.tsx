// ============================================================================
// Report Date Selector — Top bar dropdown for switching between processed reports
// ============================================================================

import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useReportList } from '@/api/hooks/useDDRHooks';
import { useDDR } from '@/contexts/DDRContext';
import { Calendar } from 'lucide-react';

const ReportDateSelector: React.FC = () => {
  const { reportDate, setReportDate } = useDDR();
  const { data: reports, isLoading } = useReportList();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/60 text-xs text-slate-400">
        <Calendar className="h-3.5 w-3.5" />
        <span>Loading reports...</span>
      </div>
    );
  }

  if (!reports || reports.length === 0) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/60 text-xs text-slate-400">
        <Calendar className="h-3.5 w-3.5" />
        <span>No reports</span>
      </div>
    );
  }

  return (
    <Select value={reportDate} onValueChange={setReportDate}>
      <SelectTrigger className="w-[200px] h-8 text-xs bg-slate-800/60 border-slate-700/60">
        <div className="flex items-center gap-2">
          <Calendar className="h-3.5 w-3.5 text-cyan-400" />
          <SelectValue placeholder="Select report date" />
        </div>
      </SelectTrigger>
      <SelectContent className="bg-slate-800 border-slate-700">
        {reports.map((report) => (
          <SelectItem
            key={report.report_date}
            value={report.report_date}
            className="text-xs"
          >
            <div className="flex items-center justify-between gap-4">
              <span>{report.report_date}</span>
              <span className="text-slate-500">{report.rigs} rigs</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                report.status === 'processed' ? 'text-emerald-400 bg-emerald-900/30' :
                report.status === 'processing' ? 'text-amber-400 bg-amber-900/30' :
                'text-red-400 bg-red-900/30'
              }`}>
                {report.status}
              </span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};

export default ReportDateSelector;
