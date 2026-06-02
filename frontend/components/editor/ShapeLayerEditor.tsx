"use client";
import { useDocumentStore } from '@/store/documentStore';

export const ShapeLayerEditor = () => {
  const { document, selectedLayerId, updateLayer } = useDocumentStore();
  const layer = document?.layers.find(l => l.id === selectedLayerId);
  
  if (!layer || (layer.type !== 'container' && layer.type !== 'connector')) return null;

  const confidence = layer.content?.confidence !== undefined ? layer.content.confidence : 1.0;
  const sourceEvidence = layer.content?.source_evidence || ['manual'];
  const isLowConfidence = layer.content?.is_low_confidence || false;

  const handleUpdateContent = (updates: any) => {
    updateLayer(layer.id, {
      content: {
        ...layer.content,
        ...updates
      }
    });
  };

  return (
    <div className="space-y-5 p-4 border-t">
      <div>
        <label className="text-xs font-bold text-slate-500 uppercase block mb-1">Layer Type</label>
        <span className="text-sm font-semibold capitalize text-slate-700 bg-slate-100 px-2 py-1 rounded">
          {layer.type}
        </span>
      </div>

      {layer.type === 'container' && (
        <>
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Shape Border Style</label>
            <select
              className="w-full border rounded p-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              value={layer.content?.container_type || 'rectangle'}
              onChange={(e) => handleUpdateContent({ container_type: e.target.value })}
            >
              <option value="rectangle">Rectangle</option>
              <option value="rounded_rectangle">Rounded Box</option>
              <option value="circle">Circle</option>
              <option value="panel">Large Panel</option>
              <option value="border">Border Region</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Associated Text Label</label>
            <input
              type="text"
              className="w-full border rounded p-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              value={layer.content?.text || ''}
              placeholder="No text bound"
              onChange={(e) => handleUpdateContent({ text: e.target.value })}
            />
            <span className="text-[10px] text-slate-400 mt-1 block">Binds title and labels together.</span>
          </div>
        </>
      )}

      {layer.type === 'connector' && (
        <>
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Line Style</label>
            <select
              className="w-full border rounded p-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              value={layer.content?.style || 'solid'}
              onChange={(e) => handleUpdateContent({ style: e.target.value })}
            >
              <option value="solid">Solid Shaft</option>
              <option value="dashed">Dashed Connector</option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Directed Arrowhead</span>
            <input 
              type="checkbox" 
              checked={layer.content?.is_arrow || false}
              onChange={(e) => handleUpdateContent({ is_arrow: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded cursor-pointer"
            />
          </div>
        </>
      )}

      <div className="border-t pt-4 space-y-3">
        <div>
          <label className="text-xs font-bold text-slate-500 uppercase block mb-1">Detection Confidence</label>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-slate-200 h-2 rounded-full overflow-hidden">
              <div 
                className={`h-full ${isLowConfidence ? 'bg-orange-500' : 'bg-green-500'}`} 
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span className="text-xs font-mono font-bold text-slate-600">
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
          {isLowConfidence && (
            <span className="text-[10px] text-orange-600 font-medium block mt-1">
              ⚠️ flagged as low-confidence layer
            </span>
          )}
        </div>

        <div>
          <label className="text-xs font-bold text-slate-500 uppercase block mb-1">Source Evidence</label>
          <div className="flex flex-wrap gap-1">
            {sourceEvidence.map((ev: string) => (
              <span key={ev} className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono border border-blue-100">
                {ev}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
