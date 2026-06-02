"use client";

import { useEffect, useRef, useState } from 'react';
import useImage from 'use-image';
import {
  Arrow,
  Group,
  Image as KonvaImage,
  Layer,
  Line,
  Rect,
  Stage,
  Text,
  Transformer,
  Circle
} from 'react-konva';

import { useDocumentStore } from '@/store/documentStore';
const STAGE_WIDTH = 1280;
const STAGE_HEIGHT = 720;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const makeId = (prefix: string) =>
  `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

export const EditorCanvas = () => {
  const {
    document,
    selectedLayerId,
    selectLayer,
    updateLayer,
    deleteLayer,
    addLayer,
    pageSettings,
  } = useDocumentStore();

  const trRef = useRef<any>(null);
  const selectionRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [fitScale, setFitScale] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [isArrowToolActive, setIsArrowToolActive] = useState(false);
  const [draftConnector, setDraftConnector] = useState<{
    fixedPoints: number[];
    previewPoint: [number, number];
  } | null>(null);

  const disableInteractions = isArrowToolActive;

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';

  const imageUrl = document?.sourceImage
    ? `${backendUrl}${document.sourceImage
        .split('/')
        .map((segment) => encodeURIComponent(segment))
        .join('/')}`
        .replace(/%3A/g, ':')
        .replace(/http%3A/g, 'http:')
    : '';

  const fixedImageUrl = imageUrl.replace('http%3A//', 'http://').replace('https%3A//', 'https://');
  const [img] = useImage(fixedImageUrl, 'anonymous');

  const effectiveScale = fitScale * zoom;
  const selectedLayer =
    document?.layers?.find((item: any) => item.id === selectedLayerId) || null;
  const layers = document?.layers ?? [];

  const getTextGeometry = (layer: any) => {
    return layer.content?.text_geometry || layer.geometry;
  };

  const getContainerPadding = (layer: any) => {
    const raw = Number(layer.content?.container_padding ?? 12);
    return Number.isFinite(raw) ? Math.max(0, raw) : 12;
  };

  const setSelectedTextBorderVisible = (visible: boolean) => {
    if (!selectedLayer || selectedLayer.type !== 'text') return;

    updateLayer(selectedLayer.id, {
      content: {
        ...(selectedLayer.content || {}),
        show_border: visible,
      },
    });
  };

  const snap = (value: number) => {
    if (!pageSettings?.snapToGrid) return value;
    return Math.round(value / pageSettings.gridSize) * pageSettings.gridSize;
  };

  const duplicateSelectedLayer = () => {
    if (!document || !selectedLayerId) return;

    const layer = layers.find((item: any) => item.id === selectedLayerId);
    if (!layer) return;

    const copy = {
      ...layer,
      id: makeId(layer.type || 'layer'),
      geometry: {
        ...layer.geometry,
        x: (layer.geometry?.x || 0) + 24,
        y: (layer.geometry?.y || 0) + 24,
      },
      content: Array.isArray(layer.content)
        ? [...layer.content]
        : layer.content && typeof layer.content === 'object'
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
  };

  const moveSelectedLayer = (dx: number, dy: number) => {
    if (!document || !selectedLayerId) return;

    const layer = layers.find((item: any) => item.id === selectedLayerId);
    if (!layer) return;

    if (layer.type === 'connector') {
      moveConnectorByDelta(layer, dx, dy);
      return;
    }

    if (layer.type === 'text') {
      const textGeometry = layer.content?.text_geometry || layer.geometry;
      const nextX = (textGeometry?.x || 0) + dx;
      const nextY = (textGeometry?.y || 0) + dy;

      updateLayer(layer.id, {
        geometry: {
          ...layer.geometry,
          x: (layer.geometry?.x || 0) + dx,
          y: (layer.geometry?.y || 0) + dy,
        },
        content: {
          ...(layer.content || {}),
          text_geometry: {
            ...textGeometry,
            x: nextX,
            y: nextY,
          },
        },
      });

      const linkedContainerId = layer.content?.linked_container_id;
      const linkedContainer = linkedContainerId
        ? layers.find((item: any) => item.id === linkedContainerId)
        : null;

      if (linkedContainerId) {
        const padding = Math.max(0, Number(layer.content?.container_padding ?? 12) || 12);
        updateLayer(linkedContainerId, {
          geometry: {
            ...(linkedContainer?.geometry || {}),
            x: nextX - padding,
            y: nextY - padding,
            w: (textGeometry?.w || 0) + padding * 2,
            h: (textGeometry?.h || 0) + padding * 2,
          },
          content: {
            ...(linkedContainer?.content || {}),
            linked_text_id: layer.id,
            is_padded: true,
            container_padding: padding,
          },
        });
      }
      return;
    }

    updateLayer(layer.id, {
      geometry: {
        ...layer.geometry,
        x: (layer.geometry?.x || 0) + dx,
        y: (layer.geometry?.y || 0) + dy,
      },
    });
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = window.document.activeElement?.tagName;

      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedLayerId) {
        if (activeTag !== 'INPUT' && activeTag !== 'TEXTAREA') {
          deleteLayer(selectedLayerId);
        }
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
        if (activeTag !== 'INPUT' && activeTag !== 'TEXTAREA') {
          e.preventDefault();
          duplicateSelectedLayer();
        }
      }

      if (isArrowToolActive && draftConnector) {
        if (e.key === 'Escape') {
          e.preventDefault();
          handleArrowToolCancel();
          return;
        }
        if (e.key === 'Enter') {
          e.preventDefault();
          handleArrowToolFinish();
          return;
        }
      }

      if (!selectedLayerId || activeTag === 'INPUT' || activeTag === 'TEXTAREA') return;

      const step = e.shiftKey ? 10 : 1;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        moveSelectedLayer(-step, 0);
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        moveSelectedLayer(step, 0);
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        moveSelectedLayer(0, -step);
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        moveSelectedLayer(0, step);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    document,
    selectedLayerId,
    deleteLayer,
    addLayer,
    updateLayer,
    pageSettings,
    isArrowToolActive,
    draftConnector,
    handleArrowToolCancel,
    handleArrowToolFinish,
  ]);

  useEffect(() => {
    const handleResize = () => {
      if (!containerRef.current) return;

      const containerWidth = containerRef.current.offsetWidth - 80;
      const containerHeight = containerRef.current.offsetHeight - 80;

      const scaleX = containerWidth / STAGE_WIDTH;
      const scaleY = containerHeight / STAGE_HEIGHT;
      const nextScale = Math.min(scaleX, scaleY, 1);

      setFitScale(nextScale);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [document]);

  useEffect(() => {
    if (selectedLayerId && trRef.current && selectionRef.current) {
      trRef.current.nodes([selectionRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [selectedLayerId, document]);

  useEffect(() => {
    if (!document) return;
    

    layers.forEach((layer: any) => {
      if (layer.type !== 'text') return;
      if (layer.content?.text_geometry) return;

      updateLayer(layer.id, {
        content: {
          ...(layer.content || {}),
          text_geometry: {
            x: layer.geometry?.x || 0,
            y: layer.geometry?.y || 0,
            w: layer.geometry?.w || 0,
            h: layer.geometry?.h || 0,
          },
        },
      });
    });
  }, [document, updateLayer]);


  const renderGrid = () => {
    if (!pageSettings?.showGrid) return null;

    const lines = [];
    const step = pageSettings.gridSize || 20;

    for (let x = 0; x <= STAGE_WIDTH; x += step) {
      lines.push(
        <Rect
          key={`grid-v-${x}`}
          x={x}
          y={0}
          width={1}
          height={STAGE_HEIGHT}
          fill="#e2e8f0"
          listening={false}
        />
      );
    }

    for (let y = 0; y <= STAGE_HEIGHT; y += step) {
      lines.push(
        <Rect
          key={`grid-h-${y}`}
          x={0}
          y={y}
          width={STAGE_WIDTH}
          height={1}
          fill="#e2e8f0"
          listening={false}
        />
      );
    }

    return lines;
  };



  const getCanvasPoint = (stage: any) => {
    const pos = stage?.getPointerPosition?.();
    if (!pos) return null;

    return {
      x: snap(pos.x / effectiveScale),
      y: snap(pos.y / effectiveScale),
    };
  };

  const buildManualConnectorPoints = (fixedPoints: number[], previewPoint: [number, number]) => {
    const points = [...fixedPoints];
    const lastX = points[points.length - 2];
    const lastY = points[points.length - 1];

    if (points.length < 2 || lastX !== previewPoint[0] || lastY !== previewPoint[1]) {
      points.push(previewPoint[0], previewPoint[1]);
    }

    return points;
  };

  const startDraftConnector = (point: { x: number; y: number }) => {
    setDraftConnector({
      fixedPoints: [point.x, point.y],
      previewPoint: [point.x, point.y],
    });
  };

  const advanceDraftConnector = (point: { x: number; y: number }) => {
    setDraftConnector((current) => {
      if (!current) return current;
      return {
        fixedPoints: current.fixedPoints,
        previewPoint: [point.x, point.y],
      };
    });
  };

  const commitDraftConnectorPoint = (point: { x: number; y: number }) => {
    setDraftConnector((current) => {
      if (!current) return current;
      return {
        fixedPoints: [...current.fixedPoints, point.x, point.y],
        previewPoint: [point.x, point.y],
      };
    });
  };

  const cancelDraftConnector = () => {
    setDraftConnector(null);
  };

  const finishDraftConnector = () => {
    setDraftConnector((current) => {
      if (!current) return current;

      const finalPoints = buildManualConnectorPoints(
        current.fixedPoints,
        current.previewPoint
      ).map((value) => Number(value) || 0);

      if (finalPoints.length < 4) {
        return null;
      }

      addLayer({
        id: makeId('connector'),
        type: 'connector',
        geometry: getConnectorBBox(finalPoints),
        content: {
          points: finalPoints,
          endpoints: finalPoints,
          route_mode: 'manual',
          direction: 'forward',
          style: 'solid',
          manual_offset: { x: 0, y: 0 },
          source_layer_id: null,
          target_layer_id: null,
          source_anchor: null,
          target_anchor: null,
          free_source_point: [finalPoints[0], finalPoints[1]],
          free_target_point: [finalPoints[finalPoints.length - 2], finalPoints[finalPoints.length - 1]],
        },
        style: {
          stroke: '#ef4444',
          strokeWidth: 2,
        },
      });

      return null;
    });
  };

  function handleArrowToolMouseDown(e: any) {
    if (!isArrowToolActive) return;

    if (e.evt?.detail === 2) return;

    const stage = e.target?.getStage?.();
    const point = getCanvasPoint(stage);
    if (!point) return;

    e.cancelBubble = true;

    if (!draftConnector) {
      startDraftConnector(point);
      return;
    }

    commitDraftConnectorPoint(point);
  };

  function handleArrowToolMouseMove(e: any) {
    if (!isArrowToolActive || !draftConnector) return;

    const stage = e.target?.getStage?.();
    const point = getCanvasPoint(stage);
    if (!point) return;

    advanceDraftConnector(point);
  };

  function handleArrowToolFinish() {
    if (!isArrowToolActive || !draftConnector) return;
    finishDraftConnector();
  };

  function handleArrowToolCancel() {
    if (!isArrowToolActive) return;
    cancelDraftConnector();
  }

const getConnectorPoints = (layer: any, overrideContent?: any): number[] => {
  const content = {
    ...(layer.content || {}),
    ...(overrideContent || {}),
  };

  const storedPoints = content.points || content.endpoints || [];
  const routeOffset = content.manual_offset || { x: 0, y: 0 };
  const routeMode =
    content.route_mode ||
    (content.source_layer_id || content.target_layer_id ? 'orthogonal' : 'straight');

  const toPointArray = (value: any): number[] | null => {
    if (Array.isArray(value) && value.length >= 2 && typeof value[0] === 'number') {
      return [Number(value[0]) || 0, Number(value[1]) || 0];
    }
    return null;
  };

  const getLayerGeometry = (item: any) => ({
    x: Number(item?.geometry?.x || 0),
    y: Number(item?.geometry?.y || 0),
    w: Math.max(1, Number(item?.geometry?.w || 1)),
    h: Math.max(1, Number(item?.geometry?.h || 1)),
  });

  const getAnchorPoint = (item: any, other: any, preferred?: string): [number, number] => {
    const geom = getLayerGeometry(item);
    const otherGeom = other ? getLayerGeometry(other) : null;
    const cx = geom.x + geom.w / 2;
    const cy = geom.y + geom.h / 2;

    const fromPreferred = (side: string): [number, number] => {
      switch (side) {
        case 'left':
          return [geom.x, cy];
        case 'right':
          return [geom.x + geom.w, cy];
        case 'top':
          return [cx, geom.y];
        case 'bottom':
          return [cx, geom.y + geom.h];
        default:
          return [geom.x + geom.w, cy];
      }
    };

    if (preferred) {
      return fromPreferred(preferred);
    }

    if (!otherGeom) {
      return [geom.x + geom.w, cy];
    }

    const ocx = otherGeom.x + otherGeom.w / 2;
    const ocy = otherGeom.y + otherGeom.h / 2;
    const dx = ocx - cx;
    const dy = ocy - cy;

    if (Math.abs(dx) >= Math.abs(dy)) {
      return dx >= 0 ? [geom.x + geom.w, cy] : [geom.x, cy];
    }

    return dy >= 0 ? [cx, geom.y + geom.h] : [cx, geom.y];
  };

  const buildOrthogonal = (start: [number, number], end: [number, number]): number[] => {
    const [x1, y1] = start;
    const [x2, y2] = end;

    if (Math.abs(x2 - x1) >= Math.abs(y2 - y1)) {
      const midX = (x1 + x2) / 2;
      return [x1, y1, midX, y1, midX, y2, x2, y2];
    }

    const midY = (y1 + y2) / 2;
    return [x1, y1, x1, midY, x2, midY, x2, y2];
  };

  const sourceLayer = content.source_layer_id
    ? layers.find((item: any) => item.id === content.source_layer_id) || null
    : null;
  const targetLayer = content.target_layer_id
    ? layers.find((item: any) => item.id === content.target_layer_id) || null
    : null;

  const freeSource = toPointArray(content.free_source_point);
  const freeTarget = toPointArray(content.free_target_point);

  let basePoints: number[] | null = null;

  if (routeMode === 'manual' && Array.isArray(storedPoints) && typeof storedPoints[0] === 'number' && storedPoints.length >= 4) {
    const start: [number, number] = sourceLayer
      ? getAnchorPoint(sourceLayer, targetLayer, content.source_anchor)
      : (freeSource || [Number(storedPoints[0]) || 0, Number(storedPoints[1]) || 0]) as [number, number];

    const end: [number, number] = targetLayer
      ? getAnchorPoint(targetLayer, sourceLayer, content.target_anchor)
      : (freeTarget || [
          Number(storedPoints[storedPoints.length - 2]) || 0,
          Number(storedPoints[storedPoints.length - 1]) || 0,
        ]) as [number, number];

    const middlePoints = storedPoints.length > 4 ? storedPoints.slice(2, -2) : [];
    basePoints = [start[0], start[1], ...middlePoints, end[0], end[1]];
  } else if (sourceLayer || targetLayer || freeSource || freeTarget) {
    const start: [number, number] = sourceLayer
      ? getAnchorPoint(sourceLayer, targetLayer, content.source_anchor)
      : (freeSource || (Array.isArray(storedPoints) && typeof storedPoints[0] === 'number'
          ? [Number(storedPoints[0]) || 0, Number(storedPoints[1]) || 0]
          : [Number(layer.geometry?.x || 0), Number(layer.geometry?.y || 0)])) as [number, number];

    const end: [number, number] = targetLayer
      ? getAnchorPoint(targetLayer, sourceLayer, content.target_anchor)
      : (freeTarget || (Array.isArray(storedPoints) && typeof storedPoints[0] === 'number' && storedPoints.length >= 4
          ? [Number(storedPoints[2]) || 0, Number(storedPoints[3]) || 0]
          : [Number(layer.geometry?.x || 0) + Number(layer.geometry?.w || 0), Number(layer.geometry?.y || 0)])) as [number, number];

    basePoints = routeMode === 'orthogonal'
      ? buildOrthogonal(start, end)
      : [start[0], start[1], end[0], end[1]];
  } else if (Array.isArray(storedPoints) && typeof storedPoints[0] === 'number' && storedPoints.length >= 4) {
    basePoints = storedPoints.map((value: any) => Number(value) || 0);
  } else if (Array.isArray(storedPoints) && Array.isArray(storedPoints[0])) {
    basePoints = storedPoints.flat().map((value: any) => Number(value) || 0);
  } else {
    basePoints = [
      Number(layer.geometry?.x || 0),
      Number(layer.geometry?.y || 0),
      Number(layer.geometry?.x || 0) + Number(layer.geometry?.w || 0),
      Number(layer.geometry?.y || 0),
    ];
  }

  const ox = Number(routeOffset.x || 0);
  const oy = Number(routeOffset.y || 0);

  return basePoints.map((value: number, index: number) => (index % 2 === 0 ? value + ox : value + oy));
};

const normalizeConnectorPoints = (layer: any): number[] => {
  return getConnectorPoints(layer);
};

const getConnectorBBox = (points: number[]) => {
  const xs: number[] = [];
  const ys: number[] = [];

  for (let i = 0; i < points.length; i += 2) {
    xs.push(Number(points[i]) || 0);
    ys.push(Number(points[i + 1]) || 0);
  }

  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);

  return {
    x: minX,
    y: minY,
    w: Math.max(1, maxX - minX),
    h: Math.max(1, maxY - minY),
  };
};

const commitConnectorPointsExact = (layer: any, nextPoints: number[], extraContent: any = {}) => {
  const bbox = getConnectorBBox(nextPoints);

  updateLayer(layer.id, {
    geometry: bbox,
    content: {
      ...(layer.content || {}),
      points: nextPoints,
      endpoints: nextPoints,
      ...extraContent,
    },
  });
};

const moveConnectorByDelta = (layer: any, dx: number, dy: number) => {
  const currentOffset = layer.content?.manual_offset || { x: 0, y: 0 };
  const nextOffset = {
    x: Number(currentOffset.x || 0) + dx,
    y: Number(currentOffset.y || 0) + dy,
  };

  const nextPoints = getConnectorPoints(layer).map((value: number, index: number) =>
    index % 2 === 0 ? value + dx : value + dy
  );

  updateLayer(layer.id, {
    geometry: getConnectorBBox(nextPoints),
    content: {
      ...(layer.content || {}),
      points: nextPoints,
      endpoints: nextPoints,
      manual_offset: nextOffset,
    },
  });
};

const setSelectedConnectorRouteMode = (routeMode: 'straight' | 'orthogonal') => {
  if (!selectedLayer || selectedLayer.type !== 'connector') return;

  updateLayer(selectedLayer.id, {
    content: {
      ...(selectedLayer.content || {}),
      route_mode: routeMode,
    },
  });
};

const findNearestConnectorAttachment = (x: number, y: number, excludeLayerId?: string) => {
  const layers = document?.layers || [];
  let best: any = null;
  let bestDistance = Infinity;
  let bestAnchor: 'left' | 'right' | 'top' | 'bottom' = 'right';

  for (const item of layers) {
    if (item.id === excludeLayerId) continue;
    if (!['text', 'shape', 'container', 'table'].includes(item.type)) continue;

    const gx = Number(item.geometry?.x || 0);
    const gy = Number(item.geometry?.y || 0);
    const gw = Math.max(1, Number(item.geometry?.w || 0));
    const gh = Math.max(1, Number(item.geometry?.h || 0));

    const clampedX = clamp(x, gx, gx + gw);
    const clampedY = clamp(y, gy, gy + gh);
    const distance = Math.hypot(x - clampedX, y - clampedY);

    if (distance < bestDistance) {
      bestDistance = distance;
      best = item;

      const cx = gx + gw / 2;
      const cy = gy + gh / 2;
      const dx = x - cx;
      const dy = y - cy;

      if (Math.abs(dx) >= Math.abs(dy)) {
        bestAnchor = dx >= 0 ? 'right' : 'left';
      } else {
        bestAnchor = dy >= 0 ? 'bottom' : 'top';
      }
    }
  }

  if (!best || bestDistance > 32) return null;

  return {
    layer: best,
    anchor: bestAnchor,
  };
};

const updateConnectorEndpoint = (
  layer: any,
  endpoint: 'source' | 'target',
  x: number,
  y: number
) => {
  const attachment = findNearestConnectorAttachment(x, y, layer.id);
  const nextContent: any = {
    ...(layer.content || {}),
  };

  const isManual = nextContent.route_mode === 'manual';

  if (endpoint === 'source') {
    if (attachment) {
      nextContent.source_layer_id = attachment.layer.id;
      nextContent.source_anchor = attachment.anchor;
      nextContent.free_source_point = null;
    } else {
      nextContent.source_layer_id = null;
      nextContent.source_anchor = null;
      nextContent.free_source_point = [x, y];
    }
  } else {
    if (attachment) {
      nextContent.target_layer_id = attachment.layer.id;
      nextContent.target_anchor = attachment.anchor;
      nextContent.free_target_point = null;
    } else {
      nextContent.target_layer_id = null;
      nextContent.target_anchor = null;
      nextContent.free_target_point = [x, y];
    }
  }

  const currentPoints = getConnectorPoints(layer, nextContent);

  let nextPoints = currentPoints;
  if (isManual && Array.isArray(currentPoints) && currentPoints.length >= 4) {
    nextPoints = [...currentPoints];
    if (endpoint === 'source') {
      nextPoints[0] = x;
      nextPoints[1] = y;
    } else {
      nextPoints[nextPoints.length - 2] = x;
      nextPoints[nextPoints.length - 1] = y;
    }
  }

  updateLayer(layer.id, {
    geometry: getConnectorBBox(nextPoints),
    content: {
      ...nextContent,
      route_mode: isManual ? 'manual' : nextContent.route_mode,
      points: nextPoints,
      endpoints: nextPoints,
    },
  });
};

const adjustSelectedConnectorLength = (delta: number) => {
  if (!selectedLayer || selectedLayer.type !== 'connector') return;

  const pts = normalizeConnectorPoints(selectedLayer);
  const x1 = pts[0];
  const y1 = pts[1];
  const x2 = pts[2];
  const y2 = pts[3];

  const vx = x2 - x1;
  const vy = y2 - y1;
  const len = Math.max(1, Math.hypot(vx, vy));
  const ux = vx / len;
  const uy = vy / len;

  const nextLen = Math.max(20, len + delta);
  const nextPoints = [x1, y1, x1 + ux * nextLen, y1 + uy * nextLen];

  commitConnectorPointsExact(selectedLayer, nextPoints, {
    route_mode: 'straight',
    source_layer_id: null,
    target_layer_id: null,
    free_source_point: [nextPoints[0], nextPoints[1]],
    free_target_point: [nextPoints[2], nextPoints[3]],
  });
};

const adjustSelectedConnectorThickness = (delta: number) => {
  if (!selectedLayer || selectedLayer.type !== 'connector') return;

  const current = Number(selectedLayer.style?.strokeWidth ?? 2);
  const next = Math.max(1, Math.min(20, current + delta));

  updateLayer(selectedLayer.id, {
    style: {
      ...(selectedLayer.style || {}),
      strokeWidth: next,
    },
  });
};

  return (
    <div ref={containerRef} className="flex-1 bg-slate-100 overflow-hidden flex items-center justify-center p-8">
      <div className="bg-white shadow-[0_20px_50px_rgba(8,112,184,0.1)] rounded-sm border border-slate-100">
<div className="fixed right-4 top-4 z-50 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl">
  <div className="text-sm font-semibold text-slate-900">Arrow tool</div>
  <div className="mt-1 text-xs text-slate-500">
    Turn this on, click to place the start point, keep clicking to add bends, and double-click to finish the arrow.
  </div>

  <div className="mt-4 grid grid-cols-2 gap-2">
    <button
      onClick={() => {
        setIsArrowToolActive((current) => !current);
        setDraftConnector(null);
        selectLayer(null);
      }}
      className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
    >
      {isArrowToolActive ? 'Stop arrow tool' : 'Arrow tool'}
    </button>
    <button
      onClick={handleArrowToolCancel}
      disabled={!draftConnector}
      className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
    >
      Cancel
    </button>
  </div>
</div>

{selectedLayer?.type === 'text' && (
          <div className="fixed right-4 top-4 z-50 w-72 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl">
            <div className="text-sm font-semibold text-slate-900">Text border</div>
            <div className="mt-1 text-xs text-slate-500">
              Toggle the border around the selected text only. The text itself stays editable.
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                onClick={() => setSelectedTextBorderVisible(false)}
                disabled={selectedLayer.content?.show_border === false}
                className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Remove border
              </button>
              <button
                onClick={() => setSelectedTextBorderVisible(true)}
                disabled={selectedLayer.content?.show_border !== false}
                className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Restore border
              </button>
            </div>
          </div>
        )}

        <Stage
          width={STAGE_WIDTH * effectiveScale}
          height={STAGE_HEIGHT * effectiveScale}
          scaleX={effectiveScale}
          scaleY={effectiveScale}
          onMouseDown={(e) => {
            if (isArrowToolActive) {
              handleArrowToolMouseDown(e);
              return;
            }

            if (e.target === e.target.getStage()) {
              selectLayer(null);
            }
          }}
          onMouseMove={(e) => {
            if (isArrowToolActive) {
              handleArrowToolMouseMove(e);
            }
          }}
          onDblClick={() => {
            if (isArrowToolActive) {
              handleArrowToolFinish();
            }
          }}
          onDblTap={() => {
            if (isArrowToolActive) {
              handleArrowToolFinish();
            }
          }}
          onWheel={(e) => {
            e.evt.preventDefault();
            const direction = e.evt.deltaY > 0 ? -1 : 1;
            setZoom((current) => clamp(current + direction * 0.08, 0.35, 2.5));
          }}
        >
          <Layer>
            <Rect width={STAGE_WIDTH} height={STAGE_HEIGHT} fill={pageSettings.backgroundColor} />
            {renderGrid()}
            {pageSettings.showReference && img && (
              <KonvaImage
                image={img}
                width={STAGE_WIDTH}
                height={STAGE_HEIGHT}
                opacity={pageSettings.referenceOpacity}
                listening={false}
              />
            )}
          </Layer>

          <Layer>
            {draftConnector && (
              <Arrow
                points={buildManualConnectorPoints(draftConnector.fixedPoints, draftConnector.previewPoint)}
                stroke="#ef4444"
                strokeWidth={2}
                dash={[6, 4]}
                pointerLength={10}
                pointerWidth={10}
                fill="#ef4444"
                listening={false}
              />
            )}
            
            {layers
              .filter((layer: any) => layer.type !== 'figure')
              .map((layer: any) => {
                const isSelected = selectedLayerId === layer.id;
                const style = layer.style || {};
                const shapeType = layer.content?.shape_type || 'rectangle';

                if (layer.type === 'text') {
                  const linkedContainerId = layer.content?.linked_container_id;
                  const linkedContainer = linkedContainerId
                    ? layers.find((item: any) => item.id === linkedContainerId)
                    : null;

                  const showBorder = layer.content?.show_border !== false;
                  const textGeometry = getTextGeometry(layer);

                  const syncLinkedContainer = (
                    x: number,
                    y: number,
                    w: number,
                    h: number,
                    padded: boolean
                  ) => {
                    if (!linkedContainerId) return;

                    const padding = padded ? getContainerPadding(layer) : 0;
                    const nextGeometry = {
                      ...(linkedContainer?.geometry || {
                        x: x - padding,
                        y: y - padding,
                        w: w + padding * 2,
                        h: h + padding * 2,
                      }),
                      x: x - padding,
                      y: y - padding,
                      w: w + padding * 2,
                      h: h + padding * 2,
                    };

                    updateLayer(linkedContainerId, {
                      geometry: nextGeometry,
                      content: {
                        ...(linkedContainer?.content || {}),
                        linked_text_id: layer.id,
                        is_padded: padded,
                        container_padding: padding,
                      },
                    });
                  };

                  const fontSize = style.fontSize || 16;

                  return (
                    <>
                      {showBorder && (
                        <Rect
                          key={`box_${layer.id}`}
                          id={`box_${layer.id}`}
                          x={layer.geometry.x}
                          y={layer.geometry.y}
                          width={layer.geometry.w}
                          height={layer.geometry.h}
                          fill="rgba(255,255,255,0.0)"
                          stroke={isSelected ? '#3b82f6' : '#000000'}
                          strokeWidth={2}
                          listening={true}
                          onClick={() => { if (!isArrowToolActive) selectLayer(layer.id); }}
                          ref={isSelected ? selectionRef : null}
                          onTransformEnd={() => {
                            const node = selectionRef.current;
                            const x = snap(node.x());
                            const y = snap(node.y());
                            const w = snap(node.width() * node.scaleX());
                            const h = snap(node.height() * node.scaleY());

                            updateLayer(layer.id, {
                              geometry: {
                                ...layer.geometry,
                                x,
                                y,
                                w,
                                h,
                              },
                            });

                            node.scaleX(1);
                            node.scaleY(1);
                          }}
                        />
                      )}
                      <Text
                        key={layer.id}
                        id={layer.id}
                        x={textGeometry.x}
                        y={textGeometry.y}
                        width={textGeometry.w}
                        height={textGeometry.h}
                        text={layer.content.text || ''}
                        fontSize={fontSize}
                        fontFamily={style.fontFamily || 'Arial'}
                        fontStyle={`${style.fontStyle || 'normal'} ${style.fontWeight || 'normal'}`}
                        fill={style.color || '#000000'}
                        align={style.align || 'center'}
                        verticalAlign="middle"
                        padding={0}
                        draggable={!disableInteractions}
                        onClick={() => { if (!isArrowToolActive) selectLayer(layer.id); }}
                        ref={isSelected && !showBorder ? selectionRef : null}
                        onDragMove={(e) => {
                          if (pageSettings.snapToGrid) {
                            const target = e.target;
                            target.x(snap(target.x()));
                            target.y(snap(target.y()));
                          }
                        }}
                        onDragEnd={(e) => {
                          const nextX = snap(e.target.x());
                          const nextY = snap(e.target.y());

                          const nextTextGeometry = {
                            ...textGeometry,
                            x: nextX,
                            y: nextY,
                          };

                          updateLayer(layer.id, {
                            geometry: {
                              ...layer.geometry,
                              x: nextX,
                              y: nextY,
                            },
                            content: {
                              ...(layer.content || {}),
                              text_geometry: nextTextGeometry,
                            },
                          });

                          if (showBorder && linkedContainerId) {
                            syncLinkedContainer(
                              nextX,
                              nextY,
                              textGeometry.w,
                              textGeometry.h,
                              true
                            );
                          }
                        }}
                        onTransformEnd={() => {
                          if (showBorder) {
                            return;
                          }

                          const node = selectionRef.current;
                          const x = snap(node.x());
                          const y = snap(node.y());
                          const w = snap(node.width() * node.scaleX());
                          const h = snap(node.height() * node.scaleY());

                          updateLayer(layer.id, {
                            geometry: {
                              ...layer.geometry,
                              x,
                              y,
                              w,
                              h,
                            },
                            content: {
                              ...(layer.content || {}),
                              text_geometry: {
                                ...textGeometry,
                                x,
                                y,
                                w,
                                h,
                              },
                            },
                          });

                          node.scaleX(1);
                          node.scaleY(1);
                        }}
                      />
                    </>
                  );
                }

                if (layer.type === 'table') {
                  const cells = layer.content.cells || [];
                  const rows = Math.max(...cells.map((cell: any) => cell.rowIndex), 0) + 1;
                  const cols = Math.max(...cells.map((cell: any) => cell.colIndex), 0) + 1;
                  const cellWidth = layer.geometry.w / cols;
                  const cellHeight = layer.geometry.h / rows;

                  return (
                    <Group
                      key={layer.id}
                      id={layer.id}
                      x={layer.geometry.x}
                      y={layer.geometry.y}
                      draggable={!disableInteractions}
                      onClick={() => { if (!isArrowToolActive) selectLayer(layer.id); }}
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
                            y: snap(e.target.y()),
                          },
                        });
                      }}
                    >
                      <Rect
                        width={layer.geometry.w}
                        height={layer.geometry.h}
                        fill="rgba(255, 255, 255, 0.7)"
                        stroke={isSelected ? '#3b82f6' : '#cbd5e1'}
                        strokeWidth={isSelected ? 2 : 1}
                      />

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

                if (layer.type === 'image') {
                  return (
                    <RefinedImageLayer
                      key={layer.id}
                      layer={layer}
                      mainImg={img}
                      isSelected={isSelected}
                      snap={snap}
                      disableInteractions={isArrowToolActive}
                      onSelect={() => selectLayer(layer.id)}
                      onUpdate={(updates: any) => updateLayer(layer.id, updates)}
                      backendUrl={backendUrl}
                    />
                  );
                }

                if (layer.type === 'shape' || layer.type === 'container') {
                  const isContainer = layer.type === 'container';
                  const fillColor =
                    style.fill ||
                    (isContainer ? 'rgba(241, 245, 249, 0.12)' : 'rgba(255, 255, 255, 0.1)');
                  let strokeColor = isSelected ? '#3b82f6' : (style.stroke || '#64748b');
                  let dashStyle: number[] | undefined = style.dash;
                  let strokeWidth = style.strokeWidth || 1.5;

                  if (shapeType === 'border') {
                    dashStyle = [6, 4];
                    strokeWidth = 2;
                  }

                  if (shapeType === 'diamond') {
                    const x = layer.geometry.x;
                    const y = layer.geometry.y;
                    const w = layer.geometry.w;
                    const h = layer.geometry.h;

                    const points = [
                      w / 2, 0,
                      w, h / 2,
                      w / 2, h,
                      0, h / 2,
                    ];

                    return (
                      <Line
                        key={layer.id}
                        id={layer.id}
                        x={x}
                        y={y}
                        points={points}
                        closed
                        fill={fillColor}
                        stroke={strokeColor}
                        strokeWidth={isSelected ? 2.5 : strokeWidth}
                        dash={dashStyle}
                        draggable={!disableInteractions}
                        onClick={() => { if (!isArrowToolActive) selectLayer(layer.id); }}
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
                              y: snap(e.target.y()),
                            },
                          });
                        }}
                        onTransformEnd={() => {
                          const node = selectionRef.current;
                          updateLayer(layer.id, {
                            geometry: {
                              ...layer.geometry,
                              x: snap(node.x()),
                              y: snap(node.y()),
                              w: snap(node.width() * node.scaleX()),
                              h: snap(node.height() * node.scaleY()),
                            },
                          });
                          node.scaleX(1);
                          node.scaleY(1);
                        }}
                      />
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
                      fill={fillColor}
                      stroke={strokeColor}
                      strokeWidth={isSelected ? 2.5 : strokeWidth}
                      dash={dashStyle}
                      cornerRadius={
                        shapeType === 'circle'
                          ? Math.min(layer.geometry.w, layer.geometry.h) / 2
                          : shapeType === 'ellipse'
                            ? Math.min(layer.geometry.w, layer.geometry.h) / 3
                            : shapeType === 'rounded_rectangle' || isContainer
                              ? style.cornerRadius || 12
                              : 0
                      }
                      draggable={!disableInteractions}
                      onClick={() => { if (!isArrowToolActive) selectLayer(layer.id); }}
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
                            y: snap(e.target.y()),
                          },
                        });
                      }}
                      onTransformEnd={() => {
                        const node = selectionRef.current;
                        updateLayer(layer.id, {
                          geometry: {
                            ...layer.geometry,
                            x: snap(node.x()),
                            y: snap(node.y()),
                            w: snap(node.width() * node.scaleX()),
                            h: snap(node.height() * node.scaleY()),
                          },
                        });
                        node.scaleX(1);
                        node.scaleY(1);
                      }}
                    />
                  );
                }

if (layer.type === 'connector') {
  const points = getConnectorPoints(layer);
  const routeMode =
    layer.content?.route_mode ||
    (layer.content?.source_layer_id || layer.content?.target_layer_id
      ? 'orthogonal'
      : 'straight');
  const styleValue = layer.content?.style || 'solid';
  const direction = layer.content?.direction || 'forward';
  const isArrow = direction !== 'none';
  const isDashed = styleValue === 'dashed' || styleValue === 'dotted';
  const strokeColor = isSelected ? '#3b82f6' : (style.stroke || '#ef4444');
  const dashStyle = isDashed ? [5, 5] : undefined;
  const tension = layer.content?.tension || 0;
  const strokeWidth = Number(layer.style?.strokeWidth ?? 2);

  const handleDragEnd = (e: any) => {
    const endX = e.target.x();
    const endY = e.target.y();
    const dx = endX - (layer.geometry?.x || 0);
    const dy = endY - (layer.geometry?.y || 0);

    moveConnectorByDelta(layer, dx, dy);
  };

  const commonProps = {
    key: layer.id,
    id: layer.id,
    points,
    stroke: strokeColor,
    strokeWidth,
    dash: dashStyle,
    tension,
    draggable: !isArrowToolActive,
    onClick: () => { if (!isArrowToolActive) selectLayer(layer.id); },
    ref: isSelected ? selectionRef : null,
    onDragEnd: handleDragEnd,
  } as const;

  return (
    <>
      {isArrow ? (
        <Arrow
          {...commonProps}
          pointerLength={10}
          pointerWidth={10}
          fill={strokeColor}
        />
      ) : (
        <Line {...commonProps} />
      )}

      {isSelected && (
        <>
          <Circle
            x={points[0]}
            y={points[1]}
            radius={6}
            fill="#ffffff"
            stroke="#3b82f6"
            strokeWidth={2}
            draggable={!disableInteractions}
            onDragMove={(e) => {
              updateConnectorEndpoint(layer, 'source', e.target.x(), e.target.y());
            }}
            onDragEnd={(e) => {
              updateConnectorEndpoint(layer, 'source', e.target.x(), e.target.y());
            }}
          />
          <Circle
            x={points[points.length - 2]}
            y={points[points.length - 1]}
            radius={6}
            fill="#ffffff"
            stroke="#3b82f6"
            strokeWidth={2}
            draggable={!disableInteractions}
            onDragMove={(e) => {
              updateConnectorEndpoint(layer, 'target', e.target.x(), e.target.y());
            }}
            onDragEnd={(e) => {
              updateConnectorEndpoint(layer, 'target', e.target.x(), e.target.y());
            }}
          />
        </>
      )}
    </>
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
                    fill={(layer.type as string) === 'image' ? '#f1f5f9' : '#dbeafe'}
                    stroke={isSelected ? '#3b82f6' : '#94a3b8'}
                    strokeWidth={isSelected ? 2 : 1}
                    draggable={!disableInteractions}
                    onClick={() => { if (!isArrowToolActive) selectLayer(layer.id); }}
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
                          y: snap(e.target.y()),
                        },
                      });
                    }}
                    onTransformEnd={() => {
                      const node = selectionRef.current;
                      updateLayer(layer.id, {
                        geometry: {
                          ...layer.geometry,
                          x: snap(node.x()),
                          y: snap(node.y()),
                          w: snap(node.width() * node.scaleX()),
                          h: snap(node.height() * node.scaleY()),
                        },
                      });
                      node.scaleX(1);
                      node.scaleY(1);
                    }}
                  />
                );
              })}

            {selectedLayerId && (
              <Transformer
                ref={trRef}
                rotateEnabled={false}
                enabledAnchors={[
                  'top-left',
                  'top-center',
                  'top-right',
                  'middle-right',
                  'bottom-right',
                  'bottom-center',
                  'bottom-left',
                  'middle-left',
                ]}
                boundBoxFunc={(oldBox, newBox) => {
                  if (newBox.width < 20 || newBox.height < 20) {
                    return oldBox;
                  }
                  return newBox;
                }}
              />
            )}
          </Layer>
        </Stage>
      </div>
    </div>
  );
};

// --- Sub-component for Refined Image Rendering ---

const RefinedImageLayer = ({
  layer,
  mainImg,
  isSelected,
  snap,
  disableInteractions,
  onSelect,
  onUpdate,
  backendUrl,
}: any) => {
  const [refinedImg, setRefinedImg] = useState<HTMLImageElement | null>(null);
  const [loadError, setLoadError] = useState(false);
  const selectionRef = useRef<any>(null);

  useEffect(() => {
    const refinedPath = layer.content?.refined_image_path;
    if (refinedPath) {
      const img = new window.Image();
      img.crossOrigin = 'anonymous';
      img.src = `${backendUrl}${refinedPath}`;
      img.onload = () => {
        setRefinedImg(img);
        setLoadError(false);
      };
      img.onerror = () => {
        setLoadError(true);
      };
    }
  }, [layer.content?.refined_image_path, backendUrl]);

  const useFallback = !layer.content?.refined_image_path || loadError;

  return (
    <Group
      id={layer.id}
      x={layer.geometry.x}
      y={layer.geometry.y}
      draggable={!disableInteractions}
      onClick={onSelect}
      ref={isSelected ? selectionRef : null}
      onDragMove={(e) => {
        const target = e.target;
        target.x(snap(target.x()));
        target.y(snap(target.y()));
      }}
      onDragEnd={(e) => {
        onUpdate({
          geometry: {
            ...layer.geometry,
            x: snap(e.target.x()),
            y: snap(e.target.y()),
          },
        });
      }}
    >
      {useFallback ? (
        <>
          {!mainImg && (
            <Rect
              width={layer.geometry.w}
              height={layer.geometry.h}
              fill="rgba(241, 245, 249, 0.5)"
              stroke="#94a3b8"
              strokeWidth={1}
              dash={[5, 5]}
            />
          )}
          <KonvaImage
            image={mainImg}
            width={layer.geometry.w}
            height={layer.geometry.h}
            crop={{
              x: layer.geometry.x * ((mainImg?.width || 1280) / 1280),
              y: layer.geometry.y * ((mainImg?.height || 720) / 720),
              width: layer.geometry.w * ((mainImg?.width || 1280) / 1280),
              height: layer.geometry.h * ((mainImg?.height || 720) / 720),
            }}
          />
        </>
      ) : (
        <KonvaImage image={refinedImg as any} width={layer.geometry.w} height={layer.geometry.h} />
      )}

      {isSelected && (
        <Rect width={layer.geometry.w} height={layer.geometry.h} stroke="#3b82f6" strokeWidth={2} />
      )}
    </Group>
  );
};
