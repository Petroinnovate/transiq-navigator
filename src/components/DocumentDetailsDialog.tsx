import { useEffect, useState } from "react";
import { Loader2, FileText, Hash, Clock, Calendar } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface Props {
  docId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface Details {
  fileName: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  hasDashboard: boolean;
  chunksCount: number;
  preview: string;
}

export function DocumentDetailsDialog({ docId, open, onOpenChange }: Props) {
  const [loading, setLoading] = useState(false);
  const [details, setDetails] = useState<Details | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (!open || !docId) return;
    let cancelled = false;
    setLoading(true);
    setDetails(null);

    (async () => {
      try {
        const [doc, chunks] = await Promise.all([
          api.getDocument(docId),
          api.getDocumentChunks(docId),
        ]);
        if (cancelled) return;

        const preview = chunks
          .slice(0, 3)
          .map((c) => c.text)
          .join("\n\n")
          .slice(0, 2000);

        // Pull updated_at via listDocuments fallback
        const { items } = await api.listDocuments(50);
        const row = items.find((r) => r.id === docId);

        setDetails({
          fileName: doc.document.file_name,
          status: doc.document.status,
          createdAt: doc.document.created_at,
          updatedAt: row?.updated_at ?? doc.document.created_at,
          hasDashboard: doc.document.has_dashboard,
          chunksCount: chunks.length,
          preview: preview || "No extracted text yet.",
        });
      } catch (e: any) {
        if (!cancelled)
          toast({
            title: "Failed to load details",
            description: e.message,
            variant: "destructive",
          });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [docId, open, toast]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-slate-900 border-slate-700 text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <FileText className="h-5 w-5 text-cyan-400" />
            {details?.fileName ?? "Document details"}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Extracted text preview and processing metadata.
          </DialogDescription>
        </DialogHeader>

        {loading || !details ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading…
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700">
                <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                  <Hash className="h-3 w-3" /> Chunks
                </div>
                <div className="text-white text-lg font-semibold">
                  {details.chunksCount}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700">
                <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                  <Badge variant="outline" className="text-[10px] py-0 px-1.5">
                    {details.status}
                  </Badge>
                </div>
                <div className="text-white text-sm">
                  Dashboard: {details.hasDashboard ? "Ready" : "—"}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700">
                <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                  <Calendar className="h-3 w-3" /> Uploaded
                </div>
                <div className="text-white text-sm">
                  {new Date(details.createdAt).toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700">
                <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                  <Clock className="h-3 w-3" /> Last processed
                </div>
                <div className="text-white text-sm">
                  {new Date(details.updatedAt).toLocaleString()}
                </div>
              </div>
            </div>

            <div>
              <div className="text-slate-400 text-xs mb-2 uppercase tracking-wide">
                Extracted text preview
              </div>
              <ScrollArea className="h-64 rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                <pre className="whitespace-pre-wrap text-slate-200 text-sm font-mono leading-relaxed">
                  {details.preview}
                </pre>
              </ScrollArea>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default DocumentDetailsDialog;
