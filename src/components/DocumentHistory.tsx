import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { FileText, RefreshCw, Trash2, BarChart3, Loader2, Clock, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/services/api";
import { supabase } from "@/integrations/supabase/client";
import { DocumentDetailsDialog } from "./DocumentDetailsDialog";

type Doc = Awaited<ReturnType<typeof api.listDocuments>>[number];

function statusBadge(status: string) {
  const map: Record<string, { cls: string; icon: JSX.Element; label: string }> = {
    queued: { cls: "bg-slate-500/20 text-slate-300 border-slate-500/40", icon: <Clock className="h-3 w-3" />, label: "Queued" },
    processing: { cls: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40", icon: <Loader2 className="h-3 w-3 animate-spin" />, label: "Processing" },
    processed: { cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40", icon: <CheckCircle2 className="h-3 w-3" />, label: "Processed" },
    failed: { cls: "bg-red-500/20 text-red-300 border-red-500/40", icon: <AlertCircle className="h-3 w-3" />, label: "Failed" },
  };
  const s = map[status] ?? map.queued;
  return (
    <Badge variant="outline" className={`gap-1 ${s.cls}`}>
      {s.icon}
      {s.label}
    </Badge>
  );
}

export function DocumentHistory() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const { toast } = useToast();

  const refresh = useCallback(async () => {
    try {
      const rows = await api.listDocuments(50);
      setDocs(rows);
    } catch (e: any) {
      toast({ title: "Failed to load history", description: e.message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    refresh();
    // realtime updates for tenant's documents
    const channel = supabase
      .channel("documents-history")
      .on("postgres_changes", { event: "*", schema: "public", table: "documents" }, () => {
        refresh();
      })
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [refresh]);

  const handleReprocess = async (id: string) => {
    setBusyId(id);
    try {
      await api.reprocessDocument(id);
      toast({ title: "Re-processing started", description: "Status will update shortly." });
    } catch (e: any) {
      toast({ title: "Re-process failed", description: e.message, variant: "destructive" });
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and its data?")) return;
    setBusyId(id);
    try {
      await api.deleteDocument(id);
      setDocs((d) => d.filter((x) => x.id !== id));
      toast({ title: "Document deleted" });
    } catch (e: any) {
      toast({ title: "Delete failed", description: e.message, variant: "destructive" });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white text-lg">Document History</CardTitle>
        <Button variant="ghost" size="sm" onClick={refresh} className="text-slate-400 hover:text-white">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading…
          </div>
        ) : docs.length === 0 ? (
          <p className="text-slate-400 text-sm py-6 text-center">No documents uploaded yet.</p>
        ) : (
          <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
            {docs.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between p-3 bg-slate-700/40 rounded-lg border border-slate-600 hover:border-slate-500 transition-colors"
              >
                <div className="flex items-center space-x-3 min-w-0 flex-1">
                  <FileText className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-white text-sm font-medium truncate" title={d.file_name}>{d.file_name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {statusBadge(d.status)}
                      <span className="text-xs text-slate-500">
                        {new Date(d.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {d.has_dashboard && (
                    <Button
                      asChild
                      variant="ghost"
                      size="sm"
                      className="text-cyan-300 hover:text-cyan-200 hover:bg-cyan-500/10"
                    >
                      <Link to={`/dashboard?doc=${d.id}`}>
                        <BarChart3 className="h-4 w-4" />
                      </Link>
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busyId === d.id || d.status === "processing"}
                    onClick={() => handleReprocess(d.id)}
                    className="text-slate-300 hover:text-white hover:bg-slate-600"
                    title="Re-run processing"
                  >
                    {busyId === d.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busyId === d.id}
                    onClick={() => handleDelete(d.id)}
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default DocumentHistory;
