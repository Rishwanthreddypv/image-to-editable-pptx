export interface Geometry {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type LayerType = 'text' | 'table' | 'figure' | 'image' | 'shape' | 'container' | 'connector';

export interface DocumentLayer {
  id: string;
  type: LayerType;
  geometry: Geometry;
  content: any; // TODO: Define specific content types for Text, Table, etc.
}

export interface EditableLayeredDocument {
  version: string;
  metadata: {
    width: number;
    height: number;
  };
  layers: DocumentLayer[];
}
