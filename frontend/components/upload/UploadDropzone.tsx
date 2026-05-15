"use client";
import React, { useRef } from 'react';
import { Upload, Image as ImageIcon } from 'lucide-react';

interface UploadDropzoneProps {
  onFileSelect: (file: File) => void;
}

export const UploadDropzone = ({ onFileSelect }: UploadDropzoneProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      onFileSelect(file);
    }
  };

  return (
    <div 
      className="border-2 border-dashed border-slate-300 rounded-2xl p-12 transition-all hover:border-blue-500 hover:bg-blue-50/50 flex flex-col items-center justify-center cursor-pointer group"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <input 
        type="file" 
        className="hidden" 
        ref={fileInputRef} 
        accept="image/*"
        onChange={(e) => e.target.files?.[0] && onFileSelect(e.target.files[0])}
      />
      <div className="bg-blue-100 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform">
        <Upload className="text-blue-600 w-8 h-8" />
      </div>
      <h3 className="text-xl font-semibold mb-2">Click or drag image to upload</h3>
      <p className="text-slate-500">Supports PNG, JPG, WEBP</p>
    </div>
  );
};
