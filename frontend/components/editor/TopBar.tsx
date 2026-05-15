"use client";
import { Download, Save, Undo, Redo, Home, Keyboard, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useDocumentStore } from '@/store/documentStore';
import { useEffect, useState } from 'react';
import { documentApi } from '@/lib/api';

export const TopBar = () => {
  const { undo, redo, historyIndex, history, document, pageSettings } = useDocumentStore();
  const [isExporting, setIsExporting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        if (e.shiftKey) redo();
        else undo();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, document, pageSettings]);

  const handleSave = async () => {
    if (!document) return;
    setIsSaving(true);
    try {
      await documentApi.updateDocument(document.id, document.layers, pageSettings.backgroundColor);
    } catch (err) {
      console.error("Save failed", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = async () => {
    if (!document) return;
    setIsExporting(true);
    try {
      // Always save before exporting to ensure backend has latest edits
      await handleSave();
      await documentApi.exportPptx(document.id);
    } catch (err) {
      console.error("Export failed", err);
      alert("Failed to export PPTX. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  const viewReport = async () => {
    if (!document) return;
    try {
      const status = await documentApi.getDocumentStatus(document.id);
      const report = status.skipped_elements || [];
      alert("Skipped Elements Report (JSON):\n\n" + JSON.stringify(report, null, 2));
    } catch (err) {
      alert("Could not fetch report.");
    }
  };

  return (
    <div className="h-16 border-b bg-white flex items-center justify-between px-6 shrink-0 z-10 shadow-sm">
      <div className="flex items-center gap-4">
        <Link href="/" className="text-slate-500 hover:text-slate-900 transition-colors">
          <Home size={20} />
        </Link>
        <div className="h-4 w-px bg-slate-200" />
        <h1 className="font-bold text-slate-800 tracking-tight">Image to PPTX <span className="text-slate-400 font-normal">/ Project Editor</span></h1>
      </div>

      <div className="flex items-center gap-2">
        <button 
          onClick={viewReport}
          className="flex items-center gap-2 px-3 py-2 text-slate-600 hover:bg-slate-100 rounded-md transition-colors text-xs font-bold uppercase tracking-wider"
        >
          View Skip Report
        </button>
        <div className="h-4 w-px bg-slate-200 mx-1" />
        <button 
          onClick={undo}
          disabled={historyIndex <= 0}
          className="p-2 hover:bg-slate-100 rounded-md transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
          title="Undo (Ctrl+Z)"
        >
          <Undo size={18} />
        </button>
        <button 
          onClick={redo}
          disabled={historyIndex >= history.length - 1}
          className="p-2 hover:bg-slate-100 rounded-md transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
          title="Redo (Ctrl+Shift+Z)"
        >
          <Redo size={18} />
        </button>
        <div className="h-4 w-px bg-slate-200 mx-2" />
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors text-sm font-medium disabled:opacity-50"
        >
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {isSaving ? 'Saving...' : 'Save'}
        </button>
        <button 
          onClick={handleExport}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-all shadow-md hover:shadow-lg text-sm font-medium disabled:bg-blue-400"
        >
          {isExporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
          {isExporting ? 'Exporting...' : 'Export PPTX'}
        </button>
      </div>
    </div>
  );
};
