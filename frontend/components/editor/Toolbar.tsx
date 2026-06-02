"use client";

import { useState } from 'react';

import { useDocumentStore } from '@/store/documentStore';

import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Circle,
  Copy,
  Diamond,
  GitCommitHorizontal,
  Layout,
  MousePointer2,
  MoreVertical,
  Redo,
  Square,
  Text,
  Trash2,
  Undo,
} from 'lucide-react';

type ConnectorVariant = 'right' | 'left' | 'up' | 'down' | 'curved' | 'dotted' | 'orthogonal';

const makeId = (prefix: string) =>
  `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

export const Toolbar = () => {
  const {
    activeTool,
    setTool,
    document,
    selectedLayerId,
    selectLayer,
    deleteLayer,
    addLayer,
    undo,
    redo,
    historyIndex,
    history,
  } = useDocumentStore();

  const [expanded, setExpanded] = useState(true);

  const insertLayer = (layer: any) => {
    addLayer(layer);
    setTool('select');
  };

  const duplicateSelectedLayer = () => {
    if (!document || !selectedLayerId) return;

    const layer = document.layers?.find((item: any) => item.id === selectedLayerId);
    if (!layer) return;

    const copy = {
      ...layer,
      id: makeId(layer.type || 'layer'),
      geometry: {
        ...layer.geometry,
        x: (layer.geometry?.x || 0) + 24,
        y: (layer.geometry?.y || 0) + 24,
      },
      content:
        layer.content && typeof layer.content === 'object'
          ? {
              ...layer.content,
              points: Array.isArray(layer.content.points)
                ? layer.content.points.map((pt: any) =>
                    Array.isArray(pt) ? [pt[0] + 24, pt[1] + 24] : pt
                  )
                : layer.content.points,
              endpoints: Array.isArray(layer.content.endpoints)
                ? layer.content.endpoints.map((pt: any) =>
                    Array.isArray(pt) ? [pt[0] + 24, pt[1] + 24] : pt
                  )
                : layer.content.endpoints,
            }
          : layer.content,
    };

    addLayer(copy);
    selectLayer(copy.id);
    setTool('select');
  };

  const createShape = (shapeType: string) => {
    const id = makeId(shapeType);
    const isContainer = shapeType === 'container';

    insertLayer({
      id,
      type: isContainer ? 'container' : 'shape',
      geometry: {
        x: 180,
        y: 140,
        w: shapeType === 'circle' ? 120 : shapeType === 'ellipse' ? 160 : 140,
        h: shapeType === 'circle' ? 120 : shapeType === 'ellipse' ? 100 : 90,
      },
      content: {
        shape_type: shapeType,
        editable: true,
        confidence: 1.0,
      },
      style: {
        stroke: '#000000',
        strokeWidth: 2,
        fill: isContainer ? 'rgba(241,245,249,0.15)' : 'rgba(255,255,255,0.08)',
        cornerRadius: shapeType === 'rounded_rectangle' || isContainer ? 12 : 0,
      },
    });
  };

  const createText = () => {
    const id = makeId('text');

    insertLayer({
      id,
      type: 'text',
      geometry: {
        x: 200,
        y: 160,
        w: 180,
        h: 40,
      },
      content: {
        text: 'Double click to edit',
        editable: true,
        confidence: 1.0,
      },
      style: {
        fontSize: 18,
        color: '#111827',
        fontFamily: 'Arial',
        fontStyle: 'normal',
        fontWeight: 'normal',
      },
    });
  };

  const createTable = () => {
    const id = makeId('table');

    insertLayer({
      id,
      type: 'table',
      geometry: {
        x: 220,
        y: 180,
        w: 320,
        h: 160,
      },
      content: {
        editable: true,
        confidence: 1.0,
        cells: [
          { id: `${id}_r0c0`, rowIndex: 0, colIndex: 0, content: 'Cell 1' },
          { id: `${id}_r0c1`, rowIndex: 0, colIndex: 1, content: 'Cell 2' },
          { id: `${id}_r1c0`, rowIndex: 1, colIndex: 0, content: 'Cell 3' },
          { id: `${id}_r1c1`, rowIndex: 1, colIndex: 1, content: 'Cell 4' },
        ],
      },
      style: {
        stroke: '#cbd5e1',
        strokeWidth: 1,
        fill: 'rgba(255,255,255,0.7)',
      },
    });
  };

  const createConnector = (variant: ConnectorVariant) => {
    const id = makeId(`connector_${variant}`);

    const base = {
      x: 120,
      y: 120,
      w: 180,
      h: 90,
    };

    let points: any = [
      [100, 100],
      [240, 100],
    ];
    let style = 'solid';
    let tension = 0;

    switch (variant) {
      case 'left':
        points = [
          [240, 100],
          [100, 100],
        ];
        break;
      case 'up':
        points = [
          [100, 220],
          [100, 100],
        ];
        break;
      case 'down':
        points = [
          [100, 100],
          [100, 220],
        ];
        break;
      case 'curved':
        points = [
          [100, 100],
          [190, 60],
          [260, 160],
        ];
        tension = 0.45;
        break;
      case 'dotted':
        points = [
          [100, 100],
          [240, 100],
        ];
        style = 'dashed';
        break;
      case 'orthogonal':
        points = [
          [100, 100],
          [180, 100],
          [180, 180],
          [260, 180],
        ];
        break;
      default:
        points = [
          [100, 100],
          [240, 100],
        ];
        break;
    }

    insertLayer({
      id,
      type: 'connector',
      geometry: {
        x: base.x,
        y: base.y,
        w: base.w,
        h: base.h,
      },
      content: {
        points,
        endpoints: points,
        direction: variant === 'orthogonal' ? 'right' : variant,
        editable: true,
        confidence: 1.0,
        style,
        tension,
      },
      style: {
        stroke: '#111827',
        strokeWidth: 2,
        dash: style === 'dashed' ? [6, 4] : undefined,
      },
    });
  };

  const shapeTools = [
    { id: 'rectangle', icon: Square, label: 'Rectangle', action: () => createShape('rectangle') },
    { id: 'rounded_rectangle', icon: Layout, label: 'Rounded Rect', action: () => createShape('rounded_rectangle') },
    { id: 'circle', icon: Circle, label: 'Circle', action: () => createShape('circle') },
    { id: 'ellipse', icon: Circle, label: 'Ellipse', action: () => createShape('ellipse') },
    { id: 'diamond', icon: Diamond, label: 'Diamond', action: () => createShape('diamond') },
    { id: 'container', icon: Layout, label: 'Container', action: () => createShape('container') },
    { id: 'text', icon: Text, label: 'Text', action: createText },
    { id: 'table', icon: Layout, label: 'Table', action: createTable },
  ];

  const connectorTools = [
    { id: 'right', icon: ArrowRight, label: 'Right Arrow' },
    { id: 'left', icon: ArrowLeft, label: 'Left Arrow' },
    { id: 'up', icon: ArrowUp, label: 'Up Arrow' },
    { id: 'down', icon: ArrowDown, label: 'Down Arrow' },
    { id: 'curved', icon: GitCommitHorizontal, label: 'Curved Arrow' },
    { id: 'orthogonal', icon: Layout, label: 'Orthogonal' },
    { id: 'dotted', icon: MoreVertical, label: 'Dotted Arrow' },
  ];

  const canDelete = Boolean(selectedLayerId);
  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  return (
    <>
      <button
        onClick={() => setExpanded(!expanded)}
        className="
          fixed
          left-4
          top-4
          z-50
          bg-white
          border
          border-slate-200
          shadow-xl
          rounded-xl
          p-3
          hover:bg-slate-50
          transition-all
        "
        aria-label="Toggle toolbar"
      >
        {expanded ? <ChevronLeft size={22} /> : <ChevronRight size={22} />}
      </button>

      <div
        className={`
          fixed
          left-4
          top-16
          z-40
          bg-white
          border
          border-slate-200
          shadow-2xl
          rounded-2xl
          p-3
          flex
          flex-col
          gap-3
          transition-all
          duration-300
          max-h-[calc(100vh-5rem)]
          overflow-y-auto
          ${
            expanded
              ? 'translate-x-0 opacity-100'
              : '-translate-x-[120%] opacity-0 pointer-events-none'
          }
        `}
      >
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold text-slate-500 px-2">SELECTION</p>

          <button
            onClick={() => setTool('select')}
            className={`
              flex
              items-center
              gap-3
              px-4
              py-3
              rounded-xl
              transition-all
              ${
                activeTool === 'select'
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-100 text-slate-700'
              }
            `}
          >
            <MousePointer2 size={20} />
            <span className="text-sm font-medium">Select</span>
          </button>

          <button
            onClick={() => selectedLayerId && deleteLayer(selectedLayerId)}
            disabled={!canDelete}
            className={`
              flex
              items-center
              gap-3
              px-4
              py-3
              rounded-xl
              transition-all
              ${
                canDelete
                  ? 'text-red-500 hover:bg-red-50'
                  : 'text-slate-300 cursor-not-allowed'
              }
            `}
          >
            <Trash2 size={20} />
            <span className="text-sm font-medium">Delete</span>
          </button>

          <div className="flex gap-2">
            <button
              onClick={undo}
              disabled={!canUndo}
              className={`
                flex-1
                flex
                items-center
                justify-center
                gap-2
                px-3
                py-3
                rounded-xl
                transition-all
                ${
                  canUndo
                    ? 'hover:bg-slate-100 text-slate-700'
                    : 'text-slate-300 cursor-not-allowed'
                }
              `}
            >
              <Undo size={18} />
            </button>

            <button
              onClick={redo}
              disabled={!canRedo}
              className={`
                flex-1
                flex
                items-center
                justify-center
                gap-2
                px-3
                py-3
                rounded-xl
                transition-all
                ${
                  canRedo
                    ? 'hover:bg-slate-100 text-slate-700'
                    : 'text-slate-300 cursor-not-allowed'
                }
              `}
            >
              <Redo size={18} />
            </button>
          </div>

          <button
            onClick={duplicateSelectedLayer}
            disabled={!selectedLayerId}
            className={`
              flex
              items-center
              gap-3
              px-4
              py-3
              rounded-xl
              transition-all
              ${
                selectedLayerId
                  ? 'hover:bg-slate-100 text-slate-700'
                  : 'text-slate-300 cursor-not-allowed'
              }
            `}
          >
            <Copy size={20} />
            <span className="text-sm font-medium">Duplicate</span>
          </button>
        </div>

        <div className="h-px bg-slate-200" />

        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold text-slate-500 px-2">SHAPES</p>

          {shapeTools.map((tool) => (
            <button
              key={tool.id}
              onClick={tool.action}
              className={`
                flex
                items-center
                gap-3
                px-4
                py-3
                rounded-xl
                transition-all
                hover:bg-slate-100
                text-slate-700
              `}
            >
              <tool.icon size={20} />
              <span className="text-sm font-medium">{tool.label}</span>
            </button>
          ))}
        </div>

        <div className="h-px bg-slate-200" />

        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold text-slate-500 px-2">CONNECTORS</p>

          {connectorTools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => createConnector(tool.id as ConnectorVariant)}
              className="
                flex
                items-center
                gap-3
                px-4
                py-3
                rounded-xl
                hover:bg-slate-100
                text-slate-700
                transition-all
              "
            >
              <tool.icon size={20} />
              <span className="text-sm font-medium">{tool.label}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
};
