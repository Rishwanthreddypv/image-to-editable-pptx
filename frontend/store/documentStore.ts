import { create } from 'zustand';
import { EditableDocument, DocumentLayer, PageSettings } from '../lib/types';

interface DocumentState {
  document: EditableDocument | null;
  selectedLayerId: string | null;
  isLoading: boolean;
  history: EditableDocument[];
  historyIndex: number;
  pageSettings: PageSettings;
  activeTool: 'select' | 'rectangle' | 'container' | 'connector';
  
  setDocument: (doc: EditableDocument) => void;
  selectLayer: (id: string | null) => void;
  addLayer: (layer: DocumentLayer) => void;
  updateLayer: (id: string, updates: Partial<DocumentLayer>) => void;
  deleteLayer: (id: string) => void;
  clearDocument: () => void;
  setTool: (tool: 'select' | 'rectangle' | 'container' | 'connector') => void;
  updatePageSettings: (updates: Partial<PageSettings>) => void;
  setLoading: (loading: boolean) => void;
  
  undo: () => void;
  redo: () => void;
  pushHistory: (doc: EditableDocument) => void;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  document: null,
  selectedLayerId: null,
  isLoading: false,
  history: [],
  historyIndex: -1,
  activeTool: 'select',
  pageSettings: {
    backgroundColor: '#ffffff',
    showGrid: true,
    gridSize: 20,
    referenceOpacity: 0.2,
    showReference: true,
    snapToGrid: true,
  },

  setDocument: (doc) => set((state) => ({ 
    document: doc, 
    history: [doc], 
    historyIndex: 0,
    pageSettings: {
      ...state.pageSettings,
      backgroundColor: doc.background_color || state.pageSettings.backgroundColor
    }
  })),

  selectLayer: (id) => set({ selectedLayerId: id }),

  addLayer: (layer) => set((state) => {
    if (!state.document) return state;
    const newLayers = [...state.document.layers, layer];
    const newDoc = { ...state.document, layers: newLayers };
    
    const newHistory = state.history.slice(0, state.historyIndex + 1);
    newHistory.push(newDoc);
    
    return {
      document: newDoc,
      history: newHistory,
      historyIndex: newHistory.length - 1,
      selectedLayerId: layer.id,
      activeTool: 'select' // Auto-switch back to select after adding
    };
  }),

  updateLayer: (id, updates) => set((state) => {
    if (!state.document) return state;
    const newLayers = state.document.layers.map(l => 
      l.id === id ? { 
        ...l, 
        ...updates, 
        content: { ...l.content, ...(updates.content || {}) }, 
        style: { ...l.style, ...(updates.style || {}) } 
      } : l
    );
    const newDoc = { ...state.document, layers: newLayers };
    
    // Simple history push logic
    const newHistory = state.history.slice(0, state.historyIndex + 1);
    newHistory.push(newDoc);
    
    return {
      document: newDoc,
      history: newHistory,
      historyIndex: newHistory.length - 1
    };
  }),

  deleteLayer: (id) => set((state) => {
    if (!state.document) return state;
    const newLayers = state.document.layers.filter(l => l.id !== id);
    const newDoc = { ...state.document, layers: newLayers };
    
    const newHistory = state.history.slice(0, state.historyIndex + 1);
    newHistory.push(newDoc);
    
    return {
      document: newDoc,
      history: newHistory,
      historyIndex: newHistory.length - 1,
      selectedLayerId: state.selectedLayerId === id ? null : state.selectedLayerId
    };
  }),

  clearDocument: () => set({ 
    document: null, 
    history: [], 
    historyIndex: -1, 
    selectedLayerId: null 
  }),

  setTool: (tool) => set({ activeTool: tool }),

  updatePageSettings: (updates) => set((state) => ({
    pageSettings: { ...state.pageSettings, ...updates }
  })),

  setLoading: (loading) => set({ isLoading: loading }),

  undo: () => set((state) => {
    if (state.historyIndex <= 0) return state;
    return {
      historyIndex: state.historyIndex - 1,
      document: state.history[state.historyIndex - 1]
    };
  }),

  redo: () => set((state) => {
    if (state.historyIndex >= state.history.length - 1) return state;
    return {
      historyIndex: state.historyIndex + 1,
      document: state.history[state.historyIndex + 1]
    };
  }),

  pushHistory: (doc) => set((state) => {
    const newHistory = state.history.slice(0, state.historyIndex + 1);
    newHistory.push(doc);
    return {
      history: newHistory,
      historyIndex: newHistory.length - 1,
      document: doc
    };
  })
}));
