"use client";
import { useRouter } from "next/navigation";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { documentApi } from "@/lib/api";
import { useState } from "react";
import { Spinner } from "@/components/common/Spinner";

export default function Home() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const { project_id } = await documentApi.uploadImage(file);
      router.push(`/document/${project_id}`);
    } catch (err) {
      console.error("Upload failed", err);
      setError("Failed to upload image. Please try again.");
      setIsUploading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col items-center justify-center p-6">
      <div className="max-w-3xl w-full text-center space-y-12">
        <div className="space-y-6">
          <div className="inline-block px-4 py-1.5 rounded-full bg-blue-100 text-blue-700 font-semibold text-sm mb-4">
            AI-Powered Document Conversion
          </div>
          <h1 className="text-6xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Image to{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              Editable PPTX
            </span>
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Upload an image containing text, tables, or figures. We'll extract
            the layout and convert it into a fully layered, editable PowerPoint
            document.
          </p>
        </div>

        {isUploading ? (
          <div className="bg-white p-12 rounded-3xl shadow-2xl border border-slate-100 flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <Spinner />
            <p className="mt-6 text-slate-600 font-medium text-lg">
              Initializing workspace...
            </p>
          </div>
        ) : (
          <div className="bg-white p-2 rounded-3xl shadow-2xl border border-slate-100 animate-in fade-in duration-500">
            <UploadDropzone onFileSelect={handleFileSelect} />
          </div>
        )}

        {error && (
          <div className="text-red-500 font-medium p-4 bg-red-50 rounded-xl max-w-md mx-auto">
            {error}
          </div>
        )}
      </div>
    </main>
  );
}
