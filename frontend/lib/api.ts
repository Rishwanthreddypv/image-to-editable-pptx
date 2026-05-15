import axios from 'axios';
import { EditableDocument, DocumentLayer } from './types';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
});

export const documentApi = {
  uploadImage: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/upload/', formData);
    return data;
  },
  getDocumentStatus: async (id: string): Promise<{status: string, progress: number}> => {
    const { data } = await api.get(`/document/${id}/status`);
    return data;
  },
  getDocument: async (id: string): Promise<EditableDocument> => {
    const { data } = await api.get(`/document/${id}`);
    return data;
  },
  updateDocument: async (id: string, layers: DocumentLayer[], background_color?: string) => {
    const { data } = await api.put(`/document/${id}`, { layers, background_color });
    return data;
  },
  exportPptx: async (id: string) => {
    const response = await api.get(`/export/${id}/pptx`, {
      responseType: 'blob',
    });
    
    // Trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = window.document.createElement('a');
    link.href = url;
    link.setAttribute('download', `project_${id}.pptx`);
    window.document.body.appendChild(link);
    link.click();
    link.remove();
  }
};
