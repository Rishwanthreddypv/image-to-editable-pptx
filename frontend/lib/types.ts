export interface Geometry {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type LayerType = 'text' | 'table' | 'figure' | 'image' | 'shape';

export interface TextStyle {
  fontSize: number;
  fontFamily: string;
  fontWeight: 'normal' | 'bold';
  fontStyle: 'normal' | 'italic';
  color: string;
  align: 'left' | 'center' | 'right';
}

export interface TableCell {
  id: string;
  content: string;
  rowIndex: number;
  colIndex: number;
}

export interface DocumentLayer {
  id: string;
  type: LayerType;
  geometry: Geometry;
  content: any;
  style?: any;
}

export interface EditableDocument {
  id: string;
  layers: DocumentLayer[];
  sourceImage?: string;
  background_color?: string;
}

export interface PageSettings {
  backgroundColor: string;
  showGrid: boolean;
  gridSize: number;
  referenceOpacity: number;
  showReference: boolean;
  snapToGrid: boolean;
}
