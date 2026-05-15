"use client";
import { useDocumentStore } from '@/store/documentStore';
import { Plus, Trash2, Table as TableIcon, Layout, ChevronDown, X } from 'lucide-react';

export const TableLayerEditor = () => {
  const { document, selectedLayerId, updateLayer } = useDocumentStore();
  const layer = document?.layers.find(l => l.id === selectedLayerId);
  
  if (!layer || layer.type !== 'table') return null;

  const cells = layer.content.cells || [];
  const rows = Math.max(...cells.map((c: any) => c.rowIndex), -1) + 1;
  const cols = Math.max(...cells.map((c: any) => c.colIndex), -1) + 1;

  const updateCell = (rowIndex: number, colIndex: number, newContent: string) => {
    const newCells = [...cells];
    const cellIndex = newCells.findIndex(c => c.rowIndex === rowIndex && c.colIndex === colIndex);
    
    if (cellIndex > -1) {
      newCells[cellIndex] = { ...newCells[cellIndex], content: newContent };
    } else {
      newCells.push({ id: Math.random().toString(), rowIndex, colIndex, content: newContent });
    }
    
    updateLayer(layer.id, { content: { ...layer.content, cells: newCells } });
  };

  const addRow = () => {
    const newCells = [...cells];
    for (let c = 0; c < cols; c++) {
      newCells.push({ id: Math.random().toString(), rowIndex: rows, colIndex: c, content: "" });
    }
    updateLayer(layer.id, { content: { ...layer.content, cells: newCells } });
  };

  const addColumn = () => {
    const newCells = [...cells];
    for (let r = 0; r < rows; r++) {
      newCells.push({ id: Math.random().toString(), rowIndex: r, colIndex: cols, content: "" });
    }
    updateLayer(layer.id, { content: { ...layer.content, cells: newCells } });
  };

  const deleteRow = (targetIdx: number) => {
    if (rows <= 1) return;
    const newCells = cells
      .filter((c: any) => c.rowIndex !== targetIdx)
      .map((c: any) => ({
        ...c,
        rowIndex: c.rowIndex > targetIdx ? c.rowIndex - 1 : c.rowIndex
      }));
    updateLayer(layer.id, { content: { ...layer.content, cells: newCells } });
  };

  const deleteColumn = (targetIdx: number) => {
    if (cols <= 1) return;
    const newCells = cells
      .filter((c: any) => c.colIndex !== targetIdx)
      .map((c: any) => ({
        ...c,
        colIndex: c.colIndex > targetIdx ? c.colIndex - 1 : c.colIndex
      }));
    updateLayer(layer.id, { content: { ...layer.content, cells: newCells } });
  };

  return (
    <div className="flex flex-col h-full bg-white border-t">
      {/* Header */}
      <div className="p-4 border-b bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white shadow-sm">
            <TableIcon size={16} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Table Editor</h3>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">{rows} Rows × {cols} Columns</p>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-2">
          <button 
            onClick={addRow}
            className="flex items-center justify-center gap-2 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[11px] font-bold text-slate-600 transition-all active:scale-95 shadow-sm"
          >
            <Plus size={14} className="text-blue-600" /> Add Row
          </button>
          <button 
            onClick={addColumn}
            className="flex items-center justify-center gap-2 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[11px] font-bold text-slate-600 transition-all active:scale-95 shadow-sm"
          >
            <Plus size={14} className="text-blue-600" /> Add Column
          </button>
        </div>

        {/* Data Grid Area */}
        <div className="rounded-xl border border-slate-200 overflow-hidden shadow-inner bg-slate-100/50">
          <div className="overflow-x-auto max-h-[400px] overflow-y-auto custom-scrollbar">
            <table className="w-full border-collapse table-fixed min-w-[400px]">
              <thead className="sticky top-0 z-10">
                <tr>
                  <th className="w-12 bg-slate-100 border-b border-r border-slate-200 p-2"></th>
                  {Array.from({ length: cols }).map((_, i) => (
                    <th key={i} className="group bg-slate-100 border-b border-r border-slate-200 p-2 relative">
                      <div className="text-[10px] font-black text-slate-500">{String.fromCharCode(65 + i)}</div>
                      <button 
                        onClick={() => deleteColumn(i)}
                        className="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 p-1 bg-red-500 text-white rounded-full transition-opacity shadow-lg hover:bg-red-600"
                        title="Delete Column"
                      >
                        <X size={8} strokeWidth={4} />
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: rows }).map((_, r) => (
                  <tr key={r} className="group/row">
                    <td className="bg-slate-100 border-b border-r border-slate-200 p-2 text-center relative">
                      <span className="text-[10px] font-black text-slate-400">{r + 1}</span>
                      <button 
                        onClick={() => deleteRow(r)}
                        className="absolute top-1/2 -left-1 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 p-1 bg-red-500 text-white rounded-full transition-opacity shadow-lg hover:bg-red-600 z-10"
                        title="Delete Row"
                      >
                        <X size={8} strokeWidth={4} />
                      </button>
                    </td>
                    {Array.from({ length: cols }).map((_, c) => {
                      const cell = cells.find((cell: any) => cell.rowIndex === r && cell.colIndex === c);
                      return (
                        <td key={c} className="border-b border-r border-slate-200 p-0 bg-white focus-within:bg-blue-50/30 transition-colors">
                          <input 
                            className="w-full p-2.5 text-[11px] outline-none border-none bg-transparent text-slate-700 placeholder:text-slate-200 focus:placeholder:opacity-0"
                            value={cell?.content || ''}
                            onChange={(e) => updateCell(r, c, e.target.value)}
                            placeholder="Data..."
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Legend/Footer */}
        <div className="bg-amber-50 border border-amber-100 rounded-lg p-3">
          <div className="flex gap-2">
            <Layout size={14} className="text-amber-500 shrink-0 mt-0.5" />
            <p className="text-[10px] text-amber-700 font-medium leading-normal">
              Hover over Row numbers or Column letters to reveal the <span className="font-bold text-red-600">Delete (X)</span> button.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
