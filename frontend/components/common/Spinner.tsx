import React from 'react';

export const Spinner = ({ progress }: { progress?: number }) => (
  <div className="flex flex-col items-center justify-center">
    <div className="relative">
      <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 border-t-4 border-t-transparent border-r-4 border-r-transparent border-l-4 border-l-blue-200"></div>
      {progress !== undefined && (
        <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-blue-800">
          {Math.round(progress)}%
        </div>
      )}
    </div>
  </div>
);
