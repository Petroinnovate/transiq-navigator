import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { FileText, RefreshCw, Trash2, BarChart3, Loader2, Clock, CheckCircle2, AlertCircle, Info, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/services/api";
import { supabase } from "@/integrations/supabase/client";
import { DocumentDetailsDialog } from "./DocumentDetailsDialog";

type Doc = Awaited<ReturnType<typeof api.listDocuments>>["items"][number];

const PAGE_SIZE = 20;

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
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const { toast } = useToast();
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const filtered = docs.filter((d) => {
    const matchesQuery = !query || d.file_name.toLowerCase().includes(query.toLowerCase());
    const matchesStatus = statusFilter === "all" || d.status === statusFilter;
    return matchesQuery && matchesStatus;
  });

  const loadPage = useCallback(async (offset: number, replace: boolean) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);
    try {
      const { items, total } = await api.listDocuments(PAGE_SIZE, offset);
      setTotal(total);
      setDocs((prev) => {
        if (replace) return items;
        // Append, de-duped
        const seen = new Set(prev.map((p) => p.id));
        return [...prev, ...items.filter((i) => !seen.has(i.id))];
      });
    } catch (e: any) {
      toast({ title: "Failed to load history", description: e.message, variant: "destructive" });
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [toast]);

  const refresh = useCallback(() => loadPage(0, true), [loadPage]);

  useEffect(() => {
    refresh();
    // realtime: patch in place rather than reset scroll
    const channel = supabase
      .channel("documents-history")
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "documents" }, (payload) => {
        const row = payload.new as Doc;
        setDocs((prev) => prev.map((d) => (d.id === row.id ? { ...d, ...row } : d)));
      })
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "documents" }, (payload) => {
        const row = payload.new as Doc;
        setDocs((prev) => (prev.some((d) => d.id === row.id) ? prev : [row, ...prev]));
        setTotal((t) => t + 1);
      })
      .on("postgres_changes", { event: "DELETE", schema: "public", table: "documents" }, (payload) => {
        const row = payload.old as { id: string };
        setDocs((prev) => prev.filter((d) => d.id !== row.id));
        setTotal((t) => Math.max(0, t - 1));
      })
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [refresh]);

  // Infinite scroll via IntersectionObserver
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const hasMore = docs.length < total;
    if (!hasMore) return;
    const io = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting && !loading && !loadingMore) {
        loadPage(docs.length, false);
      }
    }, { rootMargin: "100px" });
    io.observe(el);
    return () => io.disconnect();
  }, [docs.length, total, loading, loadingMore, loadPage]);

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
      setTotal((t) => Math.max(0, t - 1));
      toast({ title: "Document deleted" });
    } catch (e: any) {
      toast({ title: "Delete failed", description: e.message, variant: "destructive" });
    } finally {
      setBusyId(null);
    }
  };

  const hasMore = docs.length < total;

  return (
    <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white text-lg">
          Document History {total > 0 && <span className="text-xs text-slate-400 font-normal">({docs.length} of {total})</span>}
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={refresh} className="text-slate-400 hover:text-white">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-3">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400 pointer-events-none" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by file name…"
              className="pl-8 bg-slate-700/40 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px] bg-slate-700/40 border-slate-600 text-white">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="processed">Processed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading…
          </div>
        ) : docs.length === 0 ? (
          <p className="text-slate-400 text-sm py-6 text-center">No documents uploaded yet.</p>
        ) : filtered.length === 0 ? (
          <p className="text-slate-400 text-sm py-6 text-center">No documents match your filters.</p>
        ) : (
          <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
            {filtered.map((d) => (
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDetailsId(d.id)}
                    className="text-slate-300 hover:text-white hover:bg-slate-600"
                    title="View details"
                  >
                    <Info className="h-4 w-4" />
                  </Button>
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
            {hasMore && (
              <div ref={sentinelRef} className="flex items-center justify-center py-3 text-slate-400 text-xs">
                {loadingMore ? (
                  <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading more…</>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => loadPage(docs.length, false)}
                    className="text-slate-400 hover:text-white"
                  >
                    Load more
                  </Button>
                )}
              </div>
            )}
            {!hasMore && docs.length > PAGE_SIZE && (
              <p className="text-center text-slate-500 text-xs py-2">End of history</p>
            )}
          </div>
        )}
      </CardContent>
      <DocumentDetailsDialog
        docId={detailsId}
        open={detailsId !== null}
        onOpenChange={(o) => !o && setDetailsId(null)}
      />
    </Card>
  );
}

export default DocumentHistory;
