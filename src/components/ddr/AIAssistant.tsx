// @ts-nocheck
// ============================================================================
// AI Q&A Module — RAG-powered natural language querying of DDR data
// Uses the existing /api/v2/search endpoint with drilling-specific prompts
// ============================================================================

import React, { useState, useRef, useEffect } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useDDRSearch } from '@/api/hooks/useDDRHooks';
import { DDR_TOKENS } from '@/styles/tokens';
import { Bot, Send, User, Loader2, Sparkles, Copy, Check, FileText } from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: { doc_id?: string; chunk_id?: string; preview?: string; score?: number }[];
}

const PROMPT_SUGGESTIONS = [
  'What was the ROP for Rig 088TE yesterday?',
  'Compare NPT hours across all rigs this week',
  'What mud weight changes were made today?',
  'Show BHA composition for the current well',
  'What are the top 3 NPT causes this month?',
  'Has there been any safety incidents lately?',
  'What is the current drilling depth progress?',
  'Summarize foreman remarks for today',
];

const AIAssistant: React.FC = () => {
  const { reportDate, selectedRigId } = useDDR();
  const searchMutation = useDDRSearch();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const query = (text || input).trim();
    if (!query) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    try {
      const result = await searchMutation.mutateAsync({
        query,
        rig_id: selectedRigId || undefined,
        report_date: reportDate || undefined,
        top_k: 5,
      });

      const answer = result?.answer || result?.response || 'No relevant results found for your query.';
      const sources = result?.sources || result?.chunks || [];

      const assistantMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: answer,
        timestamp: new Date(),
        sources: sources.map((s: Record<string, unknown>) => ({
          doc_id: s.doc_id || s.document_id,
          chunk_id: s.chunk_id || s.id,
          preview: (s.text || s.content || s.preview || '').toString().substring(0, 200),
          score: s.score || s.similarity,
        })),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      // TODO: Replace inline error with <ErrorState /> from @/components/ddr/state
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-120px)]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30">
          <Sparkles className="h-5 w-5 text-cyan-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">AI Drilling Assistant</h2>
          <p className="text-xs text-slate-400">
            Ask questions about DDR data, trends, and drilling operations
            {selectedRigId && <> • Rig: <span className="text-cyan-400">{selectedRigId}</span></>}
          </p>
        </div>
      </div>

      {/* Chat area */}
      <div
        className="flex-1 overflow-y-auto rounded-xl p-4 space-y-4 mb-4"
        style={{ background: DDR_TOKENS.bg.secondary }}
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <Bot className="h-12 w-12 text-slate-600 mb-4" />
            <h3 className="text-lg font-bold text-slate-300 mb-2">What would you like to know?</h3>
            <p className="text-sm text-slate-500 mb-6 max-w-md">
              I can answer questions about drilling operations, NPT events, mud properties,
              survey data, and more from your DDR reports.
            </p>
            <div className="grid grid-cols-2 gap-2 max-w-lg">
              {PROMPT_SUGGESTIONS.slice(0, 6).map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(suggestion)}
                  className="text-left text-xs p-3 rounded-lg border transition-colors"
                  style={{
                    background: 'rgba(6, 182, 212, 0.05)',
                    borderColor: 'rgba(6, 182, 212, 0.15)',
                  }}
                >
                  <span className="text-slate-300">{suggestion}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-cyan-500/20 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-cyan-400" />
                </div>
              )}
              <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                <div
                  className={`rounded-xl p-3 text-sm ${
                    msg.role === 'user'
                      ? 'bg-cyan-600/20 border border-cyan-500/30 text-white'
                      : 'bg-slate-800/80 border border-slate-700/50 text-slate-200'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <div className="text-[10px] uppercase text-slate-500 tracking-wider">Sources</div>
                    {msg.sources.map((src, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 text-xs p-2 rounded bg-slate-800/60 border border-slate-700/30"
                      >
                        <FileText className="h-3 w-3 text-slate-500 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <span className="text-slate-400 truncate block">
                            {src.preview || src.doc_id || 'Source document'}
                          </span>
                          {src.score != null && (
                            <span className="text-cyan-500 text-[10px]">
                              Relevance: {(src.score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Copy button for assistant messages */}
                {msg.role === 'assistant' && (
                  <button
                    onClick={() => copyToClipboard(msg.content, msg.id)}
                    className="mt-1 text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1"
                  >
                    {copiedId === msg.id ? (
                      <><Check className="h-3 w-3" /> Copied</>
                    ) : (
                      <><Copy className="h-3 w-3" /> Copy</>
                    )}
                  </button>
                )}

                <div className="text-[10px] text-slate-600 mt-1">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
              {msg.role === 'user' && (
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-600/40 flex items-center justify-center">
                  <User className="h-4 w-4 text-slate-400" />
                </div>
              )}
            </div>
          ))
        )}
        {searchMutation.isPending && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0">
              <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />
            </div>
            <div className="rounded-xl p-3 text-sm bg-slate-800/80 border border-slate-700/50 text-slate-400">
              Searching DDR data...
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div
        className="rounded-xl p-3 flex items-end gap-3"
        style={{ background: DDR_TOKENS.bg.secondary, borderTop: `1px solid ${DDR_TOKENS.surface.border}` }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about drilling operations, NPT, mud, surveys..."
          className="flex-1 bg-transparent text-white text-sm placeholder-slate-500 resize-none outline-none min-h-[40px] max-h-[120px]"
          rows={1}
          aria-label="Chat input"
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || searchMutation.isPending}
          className="p-2 rounded-lg transition-colors disabled:opacity-30"
          style={{ background: DDR_TOKENS.brand.aramcoGreen }}
          aria-label="Send message"
        >
          <Send className="h-4 w-4 text-white" />
        </button>
      </div>
    </div>
  );
};

export default AIAssistant;