"use client";
import { useDocumentStore } from '@/store/documentStore';
import { Layers, Type, Image as ImageIcon, Table, Square } from 'lucide-react';
import { clsx } from 'clsx';

export const LayerSidebar = () => {
  const { document, selectedLayerId, selectLayer } = useDocumentStore();

  const getIcon = (type: string) => {
    switch (type) {
      case 'text': return <Type size={16} />;
      case 'image': return <ImageIcon size={16} />;
      case 'table': return <Table size={16} />;
      default: return <Square size={16} />;
    }
  };

  return (
    <div className="w-64 border-r bg-white flex flex-col">
      <div className="p-4 border-b flex items-center gap-2 font-semibold">
        <Layers size={20} />
        Layers
      </div>
      <div className="flex-1 overflow-y-auto">
        {document?.layers
          .filter(layer => layer.type !== 'figure')
          .map((layer) => (
            <div
              key={layer.id}
              onClick={() => selectLayer(layer.id)}
            className={clsx(
              "px-4 py-3 flex items-center gap-3 cursor-pointer transition-colors border-b",
              selectedLayerId === layer.id ? "bg-blue-50 text-blue-700" : "hover:bg-slate-50"
            )}
          >
            {getIcon(layer.type)}
            <span className="text-sm capitalize">{layer.type} Layer</span>
          </div>
        ))}
      </div>
    </div>
  );
};
