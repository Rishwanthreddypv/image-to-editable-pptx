"use client";
import { useDocumentStore } from '@/store/documentStore';
import { Bold, Italic, AlignLeft, AlignCenter, AlignRight } from 'lucide-react';

export const TextLayerEditor = () => {
  const { document, selectedLayerId, updateLayer } = useDocumentStore();
  const layer = document?.layers.find(l => l.id === selectedLayerId);
  
  if (!layer || layer.type !== 'text') return null;

  const style = layer.style || {
    fontSize: 16,
    fontFamily: 'Arial',
    fontWeight: 'normal',
    fontStyle: 'normal',
    color: '#000000',
    align: 'left'
  };

  const updateStyle = (updates: any) => {
    updateLayer(layer.id, { style: { ...style, ...updates } });
  };

  return (
    <div className="space-y-4 p-4 border-t">
      <label className="text-xs font-bold text-slate-500 uppercase block">Text Style</label>
      
      <div className="flex gap-2">
        <select 
          className="flex-1 border rounded p-1 text-sm"
          value={style.fontFamily}
          onChange={(e) => updateStyle({ fontFamily: e.target.value })}
        >
          <option>Arial</option>
          <option>Times New Roman</option>
          <option>Courier New</option>
          <option>Inter</option>
        </select>
        <input 
          type="number" 
          className="w-16 border rounded p-1 text-sm"
          value={style.fontSize}
          onChange={(e) => updateStyle({ fontSize: parseInt(e.target.value) })}
        />
      </div>

      <div className="flex gap-1 border rounded p-1 bg-slate-50">
        <button 
          className={`p-1.5 rounded ${style.fontWeight === 'bold' ? 'bg-white shadow-sm' : ''}`}
          onClick={() => updateStyle({ fontWeight: style.fontWeight === 'bold' ? 'normal' : 'bold' })}
        >
          <Bold size={16} />
        </button>
        <button 
          className={`p-1.5 rounded ${style.fontStyle === 'italic' ? 'bg-white shadow-sm' : ''}`}
          onClick={() => updateStyle({ fontStyle: style.fontStyle === 'italic' ? 'normal' : 'italic' })}
        >
          <Italic size={16} />
        </button>
        <div className="w-px bg-slate-200 mx-1" />
        <button 
          className={`p-1.5 rounded ${style.align === 'left' ? 'bg-white shadow-sm' : ''}`}
          onClick={() => updateStyle({ align: 'left' })}
        >
          <AlignLeft size={16} />
        </button>
        <button 
          className={`p-1.5 rounded ${style.align === 'center' ? 'bg-white shadow-sm' : ''}`}
          onClick={() => updateStyle({ align: 'center' })}
        >
          <AlignCenter size={16} />
        </button>
        <button 
          className={`p-1.5 rounded ${style.align === 'right' ? 'bg-white shadow-sm' : ''}`}
          onClick={() => updateStyle({ align: 'right' })}
        >
          <AlignRight size={16} />
        </button>
      </div>

      <div>
        <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">Color</label>
        <div className="flex items-center gap-2">
          <input 
            type="color" 
            className="w-8 h-8 rounded border p-0 cursor-pointer"
            value={style.color}
            onChange={(e) => updateStyle({ color: e.target.value })}
          />
          <span className="text-sm font-mono">{style.color}</span>
        </div>
      </div>
    </div>
  );
};
