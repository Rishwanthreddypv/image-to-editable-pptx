"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useDocumentStore } from "@/store/documentStore";
import { documentApi } from "@/lib/api";
import { TopBar } from '@/components/editor/TopBar';
import { Toolbar } from '@/components/editor/Toolbar';
import { LayerSidebar } from '@/components/editor/LayerSidebar';
import { PropertyPanel } from '@/components/editor/PropertyPanel';
import { Spinner } from '@/components/common/Spinner';
import { AlertCircle } from 'lucide-react';
import dynamic from 'next/dynamic';

const EditorCanvas = dynamic(
  () => import('@/components/editor/EditorCanvas').then((mod) => mod.EditorCanvas),
  { ssr: false }
);

export default function DocumentEditor() {
  const { id } = useParams() as { id: string };
  const { document, setDocument, isLoading, setLoading } = useDocumentStore();

  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("processing");
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<any>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollStatusAndLoad = async () => {
      try {
        const result = await documentApi.getDocumentStatus(id);
        const { status: currentStatus, progress: currentProgress } = result;

        setStatus(currentStatus);
        setProgress(currentProgress);

        if (currentStatus === "completed") {
          // Document is ready, fetch it
          const doc = await documentApi.getDocument(id);
          setDocument(doc);
          setMetadata(result);
          setLoading(false);
          clearInterval(intervalId);
        } else if (currentStatus === "failed") {
          setError("Failed to process the document.");
          setLoading(false);
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Failed to poll status", err);
      }
    };

    // Initial check
    if (!document || document.id !== id) {
      setLoading(true);
      pollStatusAndLoad();
      // Poll every 1 second
      intervalId = setInterval(pollStatusAndLoad, 1000);
    }

    return () => clearInterval(intervalId);
  }, [id, document, setDocument, setLoading]);

  // Loading / Processing State
  if (isLoading || status === "processing" || status === "pending") {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-slate-50">
        <Spinner progress={progress} />
        <h2 className="mt-6 text-xl font-bold text-slate-800">
          Processing Document
        </h2>
        <p className="mt-2 text-slate-500 max-w-md text-center">
          Our AI is analyzing the layout, extracting text, and building your
          editable layers.
        </p>
      </div>
    );
  }

  // Error State
  if (error || status === "failed") {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-slate-50">
        <div className="bg-red-50 p-6 rounded-2xl flex flex-col items-center text-red-600 max-w-md text-center border border-red-100">
          <AlertCircle size={48} className="mb-4" />
          <h2 className="text-xl font-bold mb-2">Processing Failed</h2>
          <p>{error || "An unexpected error occurred during AI analysis."}</p>
        </div>
      </div>
    );
  }

  // Loaded State
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-white">
      <TopBar />
      {metadata && (
        <div className="bg-slate-50 border-b px-6 py-2 flex items-center gap-6 text-xs font-medium">
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Fidelity Score:</span>
            <span className={`px-2 py-0.5 rounded-full ${metadata.fidelity_score > 0.8 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
              {(metadata.fidelity_score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Confidence:</span>
            <span className={`px-2 py-0.5 rounded-full ${metadata.confidence_level === 'high' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
              {metadata.confidence_level.toUpperCase()}
            </span>
          </div>
          {metadata.low_resolution_flag && (
            <div className="flex items-center gap-1.5 text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100 animate-pulse">
              <AlertCircle size={12} />
              <span>Low Resolution Input</span>
            </div>
          )}
          {metadata.edge_cases_encountered?.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="w-px h-3 bg-slate-300 mx-2" />
              <div className="flex gap-2">
                {metadata.edge_cases_encountered.map((ec: string, i: number) => (
                  <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full border border-slate-200">
                    {ec}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <div className="flex-1 flex overflow-hidden relative">
        <Toolbar />
        <LayerSidebar />
        <EditorCanvas />
        <PropertyPanel />
      </div>
    </div>
  );
}
