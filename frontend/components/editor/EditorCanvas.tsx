"use client";
import { Stage, Layer, Rect, Text, Transformer, Group, Image as KonvaImage } from 'react-konva';
import { useDocumentStore } from '@/store/documentStore';
import { useEffect, useRef, useState } from 'react';
import useImage from 'use-image';

export const EditorCanvas = () => {
  const { document, selectedLayerId, selectLayer, updateLayer, pageSettings } = useDocumentStore();
  const trRef = useRef<any>(null);
  const selectionRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  
  const backendUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';
  const [img] = useImage(document?.sourceImage ? `${backendUrl}${document.sourceImage}` : '');

  // Responsive scaling logic
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.offsetWidth - 100; // padding
        const containerHeight = containerRef.current.offsetHeight - 100;
        
        const scaleX = containerWidth / 1280;
        const scaleY = containerHeight / 720;
        const newScale = Math.min(scaleX, scaleY, 1); // Don't scale up beyond 1:1
        
        setScale(newScale);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [document]);

  useEffect(() => {
    if (selectedLayerId && trRef.current && selectionRef.current) {
      trRef.current.nodes([selectionRef.current]);
      trRef.current.getLayer().batchDraw();
    }
  }, [selectedLayerId]);

  if (!document) return null;

  const snap = (value: number) => {
    if (!pageSettings.snapToGrid) return value;
    return Math.round(value / pageSettings.gridSize) * pageSettings.gridSize;
  };

  const renderGrid = () => {
    if (!pageSettings.showGrid) return null;
    const lines = [];
    const width = 1280;
    const height = 720;
    const step = pageSettings.gridSize;

    for (let i = 0; i <= width / step; i++) {
      lines.push(
        <Rect key={`v-${i}`} x={i * step} y={0} width={1} height={height} fill="#e2e8f0" listening={false} />
      );
    }
    for (let i = 0; i <= height / step; i++) {
      lines.push(
        <Rect key={`h-${i}`} x={0} y={i * step} width={width} height={1} fill="#e2e8f0" listening={false} />
      );
    }
    return lines;
  };

  return (
    <div ref={containerRef} className="flex-1 bg-slate-100 overflow-hidden flex items-center justify-center p-12">
      <div className="bg-white shadow-[0_20px_50px_rgba(8,112,184,0.1)] rounded-sm border border-slate-100">
        <Stage 
          width={1280 * scale} 
          height={720 * scale} 
          scaleX={scale}
          scaleY={scale}
          onMouseDown={(e) => {
            if (e.target === e.target.getStage()) {
              selectLayer(null);
            }
          }}
        >
          {/* Background Layer */}
          <Layer>
            <Rect width={1280} height={720} fill={pageSettings.backgroundColor} />
            {renderGrid()}
            {pageSettings.showReference && img && (
              <KonvaImage 
                image={img} 
                width={1280} 
                height={720} 
                opacity={pageSettings.referenceOpacity} 
                listening={false}
              />
            )}
          </Layer>

          {/* Content Layer */}
          <Layer>
            {document.layers.map((layer) => {
              const isSelected = selectedLayerId === layer.id;
              const style = layer.style || {};
              
              if (layer.type === 'text') {
                return (
                  <Text
                    key={layer.id}
                    id={layer.id}
                    x={layer.geometry.x}
                    y={layer.geometry.y}
                    width={layer.geometry.w}
                    height={layer.geometry.h}
                    text={layer.content.text || ''}
                    fontSize={style.fontSize || 16}
                    fontFamily={style.fontFamily || 'Arial'}
                    fontStyle={`${style.fontStyle || 'normal'} ${style.fontWeight || 'normal'}`}
                    fill={style.color || '#000000'}
                    align={style.align || 'left'}
                    draggable
                    onClick={() => selectLayer(layer.id)}
                    ref={isSelected ? selectionRef : null}
                    onDragMove={(e) => {
                      if (pageSettings.snapToGrid) {
                        const target = e.target;
                        target.x(snap(target.x()));
                        target.y(snap(target.y()));
                      }
                    }}
                    onDragEnd={(e) => {
                      updateLayer(layer.id, {
                        geometry: { 
                          ...layer.geometry, 
                          x: snap(e.target.x()), 
                          y: snap(e.target.y()) 
                        }
                      });
                    }}
                    onTransformEnd={() => {
                      const node = selectionRef.current;
                      updateLayer(layer.id, {
                        geometry: {
                          x: snap(node.x()),
                          y: snap(node.y()),
                          w: snap(node.width() * node.scaleX()),
                          h: snap(node.height() * node.scaleY())
                        }
                      });
                      node.scaleX(1);
                      node.scaleY(1);
                    }}
                  />
                );
              }

              if (layer.type === 'table') {
                const cells = layer.content.cells || [];
                const rows = Math.max(...cells.map((c: any) => c.rowIndex), 0) + 1;
                const cols = Math.max(...cells.map((c: any) => c.colIndex), 0) + 1;
                const cellWidth = layer.geometry.w / cols;
                const cellHeight = layer.geometry.h / rows;

                return (
                  <Group
                    key={layer.id}
                    id={layer.id}
                    x={layer.geometry.x}
                    y={layer.geometry.y}
                    draggable
                    onClick={() => selectLayer(layer.id)}
                    ref={isSelected ? selectionRef : null}
                    onDragMove={(e) => {
                      if (pageSettings.snapToGrid) {
                        const target = e.target;
                        target.x(snap(target.x()));
                        target.y(snap(target.y()));
                      }
                    }}
                    onDragEnd={(e) => {
                      updateLayer(layer.id, {
                        geometry: { 
                          ...layer.geometry, 
                          x: snap(e.target.x()), 
                          y: snap(e.target.y()) 
                        }
                      });
                    }}
                  >
                    {/* Table Background */}
                    <Rect
                      width={layer.geometry.w}
                      height={layer.geometry.h}
                      fill="rgba(255, 255, 255, 0.7)"
                      stroke={isSelected ? '#3b82f6' : '#cbd5e1'}
                      strokeWidth={isSelected ? 2 : 1}
                    />
                    
                    {/* Render individual cells */}
                    {cells.map((cell: any) => (
                      <Group 
                        key={cell.id} 
                        x={cell.colIndex * cellWidth} 
                        y={cell.rowIndex * cellHeight}
                      >
                        <Rect 
                          width={cellWidth} 
                          height={cellHeight} 
                          stroke="#e2e8f0" 
                          strokeWidth={0.5} 
                        />
                        <Text 
                          text={cell.content} 
                          width={cellWidth} 
                          height={cellHeight}
                          padding={5}
                          fontSize={10}
                          verticalAlign="middle"
                          fill="#1e293b"
                          ellipsis={true}
                        />
                      </Group>
                    ))}
                  </Group>
                );
              }

              return (
                <Rect
                  key={layer.id}
                  id={layer.id}
                  x={layer.geometry.x}
                  y={layer.geometry.y}
                  width={layer.geometry.w}
                  height={layer.geometry.h}
                  fill={layer.type === 'image' ? '#f1f5f9' : '#dbeafe'}
                  stroke={isSelected ? '#3b82f6' : '#94a3b8'}
                  strokeWidth={isSelected ? 2 : 1}
                  draggable
                  onClick={() => selectLayer(layer.id)}
                  ref={isSelected ? selectionRef : null}
                  onDragMove={(e) => {
                    if (pageSettings.snapToGrid) {
                      const target = e.target;
                      target.x(snap(target.x()));
                      target.y(snap(target.y()));
                    }
                  }}
                  onDragEnd={(e) => {
                    updateLayer(layer.id, {
                      geometry: { 
                        ...layer.geometry, 
                        x: snap(e.target.x()), 
                        y: snap(e.target.y()) 
                      }
                    });
                  }}
                  onTransformEnd={() => {
                    const node = selectionRef.current;
                    updateLayer(layer.id, {
                      geometry: {
                        x: snap(node.x()),
                        y: snap(node.y()),
                        w: snap(node.width() * node.scaleX()),
                        h: snap(node.height() * node.scaleY())
                      }
                    });
                    node.scaleX(1);
                    node.scaleY(1);
                  }}
                />
              );
            })}
            {selectedLayerId && <Transformer 
              ref={trRef} 
              rotateEnabled={false}
              enabledAnchors={['top-left', 'top-right', 'bottom-left', 'bottom-right']}
            />}
          </Layer>
        </Stage>
      </div>
    </div>
  );
};
