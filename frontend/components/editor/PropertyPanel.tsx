"use client";
import { useDocumentStore } from '@/store/documentStore';
import { TextLayerEditor } from './TextLayerEditor';
import { TableLayerEditor } from './TableLayerEditor';
import { ShapeLayerEditor } from './ShapeLayerEditor';
import { Settings, Maximize2, Move, Layout, Grid, Eye } from 'lucide-react';

export const PropertyPanel = () => {
  const { document, selectedLayerId, updateLayer, pageSettings, updatePageSettings } = useDocumentStore();
  const layer = document?.layers.find(l => l.id === selectedLayerId);

  if (!layer) return (
    <div className="w-72 border-l bg-white flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b font-semibold flex items-center gap-2">
        <Layout size={18} />
        Page Settings
      </div>
      <div className="p-4 space-y-6">
        <div>
          <label className="text-xs font-bold text-slate-500 uppercase block mb-3">Canvas Background</label>
          <div className="flex items-center gap-3">
            <input 
              type="color" 
              className="w-10 h-10 rounded-lg border p-1 cursor-pointer"
              value={pageSettings.backgroundColor}
              onChange={(e) => updatePageSettings({ backgroundColor: e.target.value })}
            />
            <span className="text-sm font-mono text-slate-600">{pageSettings.backgroundColor}</span>
          </div>
        </div>

        <div className="space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase block border-b pb-2 flex items-center gap-2">
            <Grid size={14} /> Grid & Snap
          </label>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Show Grid</span>
            <input 
              type="checkbox" 
              checked={pageSettings.showGrid}
              onChange={(e) => updatePageSettings({ showGrid: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Snap to Grid</span>
            <input 
              type="checkbox" 
              checked={pageSettings.snapToGrid}
              onChange={(e) => updatePageSettings({ snapToGrid: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Grid Size</label>
            <input 
              type="number" 
              className="w-full border rounded-md p-2 text-sm"
              value={pageSettings.gridSize}
              onChange={(e) => updatePageSettings({ gridSize: parseInt(e.target.value) })}
            />
          </div>
        </div>

        <div className="space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase block border-b pb-2 flex items-center gap-2">
            <Eye size={14} /> Reference Image
          </label>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Show Reference</span>
            <input 
              type="checkbox" 
              checked={pageSettings.showReference}
              onChange={(e) => updatePageSettings({ showReference: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Reference Opacity ({Math.round(pageSettings.referenceOpacity * 100)}%)</label>
            <input 
              type="range" 
              min="0" max="1" step="0.1"
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              value={pageSettings.referenceOpacity}
              onChange={(e) => updatePageSettings({ referenceOpacity: parseFloat(e.target.value) })}
            />
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="w-72 border-l bg-white flex flex-col">
      <div className="p-4 border-b font-semibold flex justify-between items-center">
        Properties
        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-[10px] uppercase font-bold">
          {layer.type}
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-6">
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Primary Content</label>
            {layer.type === 'text' ? (
              <textarea 
                className="w-full border rounded-md p-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                rows={4}
                value={layer.content.text || ''}
                onChange={(e) => updateLayer(layer.id, { content: { ...layer.content, text: e.target.value }})}
              />
            ) : (
              <div className="text-sm text-slate-500 italic bg-slate-50 p-3 rounded text-center">
                Interactive editor for {layer.type} below
              </div>
            )}
          </div>

          <div className="space-y-4">
            <label className="text-xs font-bold text-slate-500 uppercase block border-b pb-2">Geometry</label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1 flex items-center gap-1"><Move size={10} /> X</label>
                <input 
                  type="number"
                  className="w-full border rounded-md p-2 text-sm"
                  value={Math.round(layer.geometry.x)}
                  onChange={(e) => updateLayer(layer.id, { geometry: { ...layer.geometry, x: parseInt(e.target.value) }})}
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-1 flex items-center gap-1"><Move size={10} /> Y</label>
                <input 
                  type="number"
                  className="w-full border rounded-md p-2 text-sm"
                  value={Math.round(layer.geometry.y)}
                  onChange={(e) => updateLayer(layer.id, { geometry: { ...layer.geometry, y: parseInt(e.target.value) }})}
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-1 flex items-center gap-1"><Maximize2 size={10} /> Width</label>
                <input 
                  type="number"
                  className="w-full border rounded-md p-2 text-sm"
                  value={Math.round(layer.geometry.w)}
                  onChange={(e) => updateLayer(layer.id, { geometry: { ...layer.geometry, w: parseInt(e.target.value) }})}
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-1 flex items-center gap-1"><Maximize2 size={10} /> Height</label>
                <input 
                  type="number"
                  className="w-full border rounded-md p-2 text-sm"
                  value={Math.round(layer.geometry.h)}
                  onChange={(e) => updateLayer(layer.id, { geometry: { ...layer.geometry, h: parseInt(e.target.value) }})}
                />
              </div>
            </div>
          </div>
        </div>

        {layer.type === 'text' && <TextLayerEditor />}
        {layer.type === 'table' && <TableLayerEditor />}
        {(layer.type === 'container' || layer.type === 'connector') && <ShapeLayerEditor />}
      </div>
    </div>
  );
};
