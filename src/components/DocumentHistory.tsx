import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { format } from "date-fns";
import {
  FileText, RefreshCw, Trash2, BarChart3, Loader2, Clock, CheckCircle2,
  AlertCircle, Info, Search, CalendarIcon, X,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { cn } from "@/lib/utils";
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
  const [searchParams, setSearchParams] = useSearchParams();

  // Filter state synced with URL
  const query = searchParams.get("q") ?? "";
  const statusFilter = searchParams.get("status") ?? "all";
  const fromStr = searchParams.get("from") ?? "";
  const toStr = searchParams.get("to") ?? "";
  const fromDate = fromStr ? new Date(fromStr) : undefined;
  const toDate = toStr ? new Date(toStr) : undefined;

  const updateParam = useCallback((key: string, value: string | undefined) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (!value) next.delete(key);
      else next.set(key, value);
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const [docs, setDocs] = useState<Doc[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [pendingNew, setPendingNew] = useState(0);
  const { toast } = useToast();
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const isAtTop = () => {
    const el = scrollRef.current;
    return !el || el.scrollTop <= 8;
  };

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    const fromTs = fromDate ? new Date(fromDate.setHours(0, 0, 0, 0)).getTime() : null;
    const toTs = toDate ? new Date(new Date(toDate).setHours(23, 59, 59, 999)).getTime() : null;
    return docs.filter((d) => {
      if (q && !d.file_name.toLowerCase().includes(q)) return false;
      if (statusFilter !== "all" && d.status !== statusFilter) return false;
      const ts = new Date(d.created_at).getTime();
      if (fromTs !== null && ts < fromTs) return false;
      if (toTs !== null && ts > toTs) return false;
      return true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs, query, statusFilter, fromStr, toStr]);

  const loadPage = useCallback(async (offset: number, replace: boolean) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);
    try {
      const { items, total } = await api.listDocuments(PAGE_SIZE, offset);
      setTotal(total);
      setDocs((prev) => {
        if (replace) return items;
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
    const channel = supabase
      .channel("documents-history")
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "documents" }, (payload) => {
        const row = payload.new as Doc;
        setDocs((prev) => prev.map((d) => (d.id === row.id ? { ...d, ...row } : d)));
      })
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "documents" }, (payload) => {
        const row = payload.new as Doc;
        setTotal((t) => t + 1);
        // Only inject inline if user is at the top of the list; otherwise
        // queue a "new items" notice so the scroll position doesn't jump.
        if (isAtTop()) {
          setDocs((prev) => (prev.some((d) => d.id === row.id) ? prev : [row, ...prev]));
        } else {
          setPendingNew((n) => n + 1);
        }
      })
      .on("postgres_changes", { event: "DELETE", schema: "public", table: "documents" }, (payload) => {
        const row = payload.old as { id: string };
        setDocs((prev) => prev.filter((d) => d.id !== row.id));
        setSelected((s) => { const n = new Set(s); n.delete(row.id); return n; });
        setTotal((t) => Math.max(0, t - 1));
      })
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [refresh]);

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
      toast({ title: "Re-processing started" });
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
      setSelected((s) => { const n = new Set(s); n.delete(id); return n; });
      setTotal((t) => Math.max(0, t - 1));
      toast({ title: "Document deleted" });
    } catch (e: any) {
      toast({ title: "Delete failed", description: e.message, variant: "destructive" });
    } finally {
      setBusyId(null);
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  };

  const allFilteredSelected = filtered.length > 0 && filtered.every((d) => selected.has(d.id));
  const toggleSelectAll = () => {
    setSelected((s) => {
      if (allFilteredSelected) {
        const n = new Set(s);
        filtered.forEach((d) => n.delete(d.id));
        return n;
      }
      const n = new Set(s);
      filtered.forEach((d) => n.add(d.id));
      return n;
    });
  };

  const bulkReprocess = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    setBulkBusy(true);
    let ok = 0, fail = 0;
    for (const id of ids) {
      try { await api.reprocessDocument(id); ok++; } catch { fail++; }
    }
    setBulkBusy(false);
    setSelected(new Set());
    toast({
      title: `Re-processing started for ${ok} file${ok === 1 ? "" : "s"}`,
      description: fail ? `${fail} failed to queue.` : undefined,
      variant: fail ? "destructive" : "default",
    });
  };

  const bulkDelete = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    if (!confirm(`Delete ${ids.length} document${ids.length === 1 ? "" : "s"}?`)) return;
    setBulkBusy(true);
    let ok = 0, fail = 0;
    for (const id of ids) {
      try { await api.deleteDocument(id); ok++; } catch { fail++; }
    }
    setDocs((d) => d.filter((x) => !selected.has(x.id)));
    setTotal((t) => Math.max(0, t - ok));
    setSelected(new Set());
    setBulkBusy(false);
    toast({
      title: `Deleted ${ok}`,
      description: fail ? `${fail} failed.` : undefined,
      variant: fail ? "destructive" : "default",
    });
  };

  const clearFilters = () => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      ["q", "status", "from", "to"].forEach((k) => next.delete(k));
      return next;
    }, { replace: true });
  };

  const hasMore = docs.length < total;
  const hasFilters = query || statusFilter !== "all" || fromStr || toStr;

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
        <div className="flex flex-wrap gap-2 mb-3">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400 pointer-events-none" />
            <Input
              value={query}
              onChange={(e) => updateParam("q", e.target.value)}
              placeholder="Search by file name…"
              className="pl-8 bg-slate-700/40 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>
          <Select value={statusFilter} onValueChange={(v) => updateParam("status", v === "all" ? undefined : v)}>
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
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "bg-slate-700/40 border-slate-600 text-white hover:bg-slate-700 hover:text-white justify-start font-normal",
                  !fromDate && !toDate && "text-slate-400",
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {fromDate || toDate ? (
                  <span className="text-xs">
                    {fromDate ? format(fromDate, "MMM d") : "…"} – {toDate ? format(toDate, "MMM d") : "…"}
                  </span>
                ) : (
                  <span>Date range</span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="range"
                selected={{ from: fromDate, to: toDate }}
                onSelect={(range) => {
                  updateParam("from", range?.from ? range.from.toISOString().slice(0, 10) : undefined);
                  updateParam("to", range?.to ? range.to.toISOString().slice(0, 10) : undefined);
                }}
                numberOfMonths={2}
                className={cn("p-3 pointer-events-auto")}
              />
              <div className="flex justify-end p-2 border-t">
                <Button variant="ghost" size="sm" onClick={() => { updateParam("from", undefined); updateParam("to", undefined); }}>
                  Clear
                </Button>
              </div>
            </PopoverContent>
          </Popover>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="text-slate-400 hover:text-white">
              <X className="h-4 w-4 mr-1" /> Clear
            </Button>
          )}
        </div>

        {selected.size > 0 && (
          <div className="flex items-center justify-between mb-3 p-2 rounded-md bg-cyan-500/10 border border-cyan-500/30">
            <span className="text-sm text-cyan-200">{selected.size} selected</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={bulkBusy} onClick={bulkReprocess}>
                {bulkBusy ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
                Re-process
              </Button>
              <Button size="sm" variant="outline" disabled={bulkBusy} onClick={bulkDelete} className="text-red-400 hover:text-red-300">
                <Trash2 className="h-4 w-4 mr-1" /> Delete
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
                Clear
              </Button>
            </div>
          </div>
        )}

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
            <div className="flex items-center gap-2 px-3 py-1 text-xs text-slate-400">
              <Checkbox
                checked={allFilteredSelected}
                onCheckedChange={toggleSelectAll}
                aria-label="Select all"
              />
              <span>Select all visible</span>
            </div>
            {filtered.map((d) => (
              <div
                key={d.id}
                className={cn(
                  "flex items-center justify-between p-3 bg-slate-700/40 rounded-lg border transition-colors",
                  selected.has(d.id) ? "border-cyan-500/60" : "border-slate-600 hover:border-slate-500",
                )}
              >
                <div className="flex items-center space-x-3 min-w-0 flex-1">
                  <Checkbox
                    checked={selected.has(d.id)}
                    onCheckedChange={() => toggleSelect(d.id)}
                    aria-label={`Select ${d.file_name}`}
                  />
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
                    <Button asChild variant="ghost" size="sm" className="text-cyan-300 hover:text-cyan-200 hover:bg-cyan-500/10">
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
                  <Button variant="ghost" size="sm" onClick={() => loadPage(docs.length, false)} className="text-slate-400 hover:text-white">
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
