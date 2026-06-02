import base64
import copy
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncAzureOpenAI

from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_ENDPOINT,
    ENABLE_GRAPH_EXTRACTION,
    logger,
)
from app.schemas.layer import GeometryBase, Layer


class SimpleLevel2Service:
    """
    Level 2 graph compiler.

    The key change in this version is that box geometry is no longer
    delegated to the multimodal model. The model only infers connections
    between already-detected / deduplicated nodes.

    This keeps boxes stable and avoids duplicate box guessing.
    """

    def __init__(self):
        self.padding_x = 0
        self.padding_y = 0
        self.connector_gap = 40

        self.azure_endpoint = AZURE_OPENAI_ENDPOINT
        self.azure_api_key = AZURE_OPENAI_API_KEY
        self.azure_deployment = AZURE_OPENAI_DEPLOYMENT_NAME
        self.azure_api_version = AZURE_OPENAI_API_VERSION

        self.enable_graph_extraction = ENABLE_GRAPH_EXTRACTION

    async def detect_and_compile(
        self,
        image_path: str,
        project_id: str,
        l1_layers: List[Layer],
    ) -> List[Layer]:
        logger.info(f"Graph L2: compiling diagram for project {project_id}")

        if not l1_layers:
            return []

        final_layers: List[Layer] = []

        # STEP 1: Clone original layers and mark them editable.
        for layer in l1_layers:
            cloned = copy.deepcopy(layer)

            if isinstance(cloned.content, dict):
                cloned.content["editable"] = True
            else:
                cloned.content = {
                    "text": getattr(cloned.content, "text", ""),
                    "editable": True,
                }

            final_layers.append(cloned)

        # STEP 2: Deterministically remove duplicate box layers.
        # This is a geometry/content-based pass, not an LLM guess.
        final_layers = self._dedupe_layers(final_layers)

        # STEP 3: Synthesize missing parent containers from geometry only.
        # This is deterministic and only creates a container when a tight
        # stack of child nodes strongly suggests an enclosing block.
        final_layers = self._synthesize_missing_containers(final_layers)

        # STEP 4: Deterministically infer hierarchy from geometry only.
        final_layers = self._build_hierarchy_metadata(final_layers)

        # STEP 4: Build node candidates from the canonical layers.
        node_candidates = []
        for layer in final_layers:
            candidate = self._layer_to_node_candidate(layer)
            if candidate:
                node_candidates.append(candidate)

        # STEP 5: Multimodal extraction for connections only.
        graph = {"connections": []}

        if self.enable_graph_extraction and image_path:
            try:
                graph = await self._extract_connections_from_image(
                    image_path=image_path,
                    layers=node_candidates,
                )
            except Exception as exc:
                logger.exception(f"Graph extraction failed: {exc}")

        # STEP 6: Build connector layers from the returned connections.
        layers_by_id = {layer.id: layer for layer in final_layers}
        connector_layers = self._build_connector_layers(
            graph=graph,
            layers_by_id=layers_by_id,
        )

        final_layers.extend(connector_layers)

        # STEP 7: Sort layers with parents before children and connectors behind.
        final_layers.sort(
            key=lambda l: (
                0 if l.type == "connector" else 1,
                int(l.content.get("depth", 0)) if isinstance(l.content, dict) else 0,
                l.geometry.y,
                l.geometry.x,
            )
        )

        logger.info(f"Graph L2 complete. Returned {len(final_layers)} layers.")
        return final_layers

    # ---------------------------------------------------------------------
    # Deterministic box cleanup
    # ---------------------------------------------------------------------

    def _dedupe_layers(self, layers: List[Layer]) -> List[Layer]:
        """
        Merge only clear duplicates.

        Rules:
        - Only compare the same broad type family.
        - Merge when geometry overlap is very high and the content signature matches.
        - Do not try to infer semantic containers vs children here.
        """
        candidates: List[Layer] = [
            layer
            for layer in layers
            if layer.type in {"text", "shape", "container", "table"}
        ]

        if not candidates:
            return layers

        parent = list(range(len(candidates)))
        rank = [0] * len(candidates)

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra == rb:
                return
            if rank[ra] < rank[rb]:
                parent[ra] = rb
            elif rank[ra] > rank[rb]:
                parent[rb] = ra
            else:
                parent[rb] = ra
                rank[ra] += 1

        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                a = candidates[i]
                b = candidates[j]
                if a.type != b.type:
                    continue

                iou = self._bbox_iou(self._layer_bbox(a), self._layer_bbox(b))
                if iou < 0.88:
                    continue

                # Same geometry family and almost the same content => duplicate.
                if self._content_signature(a) == self._content_signature(b):
                    union(i, j)
                    continue

                # Same type + almost identical bbox is also a duplicate.
                if self._bbox_close(self._layer_bbox(a), self._layer_bbox(b)):
                    union(i, j)

        groups: Dict[int, List[Layer]] = {}
        for idx, layer in enumerate(candidates):
            root = find(idx)
            groups.setdefault(root, []).append(layer)

        canonical: List[Layer] = []
        used_ids = set()

        for group_layers in groups.values():
            best = self._pick_canonical_layer(group_layers)
            canonical.append(best)
            used_ids.add(best.id)

        # Keep all non-box layers as they are.
        extras = [layer for layer in layers if layer.type not in {"text", "shape", "container", "table"}]
        extras.extend(canonical)

        # Preserve original order as much as possible.
        order_lookup = {layer.id: idx for idx, layer in enumerate(layers)}
        extras.sort(key=lambda layer: (order_lookup.get(layer.id, 10**9), layer.geometry.y, layer.geometry.x))
        return extras

    def _pick_canonical_layer(self, group_layers: List[Layer]) -> Layer:
        """
        Deterministic tie-breaker for a duplicate group.
        """
        def priority(layer: Layer) -> Tuple[int, int, float, float]:
            text = ""
            if isinstance(layer.content, dict):
                text = str(layer.content.get("text", "")).strip()

            has_text = 1 if text else 0
            area = max(1.0, float(layer.geometry.w) * float(layer.geometry.h))

            # Higher is better:
            # 1) text-bearing layer
            # 2) table/container/shape/text preference
            type_score = {
                "table": 4,
                "container": 3,
                "shape": 2,
                "text": 1,
            }.get(layer.type, 0)

            return (has_text, type_score, area, -float(layer.geometry.y))

        return sorted(group_layers, key=priority, reverse=True)[0]

    def _layer_bbox(self, layer: Layer) -> Tuple[float, float, float, float]:
        return (
            float(layer.geometry.x),
            float(layer.geometry.y),
            max(1.0, float(layer.geometry.w)),
            max(1.0, float(layer.geometry.h)),
        )

    def _bbox_close(
        self,
        a: Tuple[float, float, float, float],
        b: Tuple[float, float, float, float],
        tol: float = 4.0,
    ) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (
            abs(ax - bx) <= tol
            and abs(ay - by) <= tol
            and abs(aw - bw) <= tol
            and abs(ah - bh) <= tol
        )

    def _bbox_iou(
        self,
        a: Tuple[float, float, float, float],
        b: Tuple[float, float, float, float],
    ) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b

        left = max(ax, bx)
        top = max(ay, by)
        right = min(ax + aw, bx + bw)
        bottom = min(ay + ah, by + bh)

        inter_w = max(0.0, right - left)
        inter_h = max(0.0, bottom - top)
        inter = inter_w * inter_h

        if inter <= 0:
            return 0.0

        area_a = aw * ah
        area_b = bw * bh
        union = max(1e-9, area_a + area_b - inter)
        return inter / union

    def _content_signature(self, layer: Layer) -> Tuple[str, str]:
        text = ""
        if isinstance(layer.content, dict):
            text = str(layer.content.get("text", "")).strip()

        text = re.sub(r"\s+", " ", text).lower()
        return (layer.type, text)

    # ---------------------------------------------------------------------
    # Deterministic container synthesis
    # ---------------------------------------------------------------------

    def _synthesize_missing_containers(self, layers: List[Layer]) -> List[Layer]:
        """
        Create a parent container only when multiple box-like children form
        a tight vertical stack. This is used to recover missing outer blocks
        in nested block diagrams.
        """
        if not layers:
            return layers

        box_layers = [
            layer
            for layer in layers
            if layer.type in {"text", "shape", "container", "table"}
            and not self._is_synthesized_container(layer)
        ]

        if len(box_layers) < 2:
            return layers

        by_id = {layer.id: layer for layer in box_layers}
        bboxes = {layer.id: self._layer_bbox(layer) for layer in box_layers}
        adjacency: Dict[str, set[str]] = {layer.id: set() for layer in box_layers}

        for i, left in enumerate(box_layers):
            for right in box_layers[i + 1 :]:
                if self._looks_like_stacked_siblings(bboxes[left.id], bboxes[right.id]):
                    adjacency[left.id].add(right.id)
                    adjacency[right.id].add(left.id)

        visited: set[str] = set()
        components: List[List[str]] = []

        for layer in box_layers:
            if layer.id in visited:
                continue

            stack = [layer.id]
            visited.add(layer.id)
            component: List[str] = []

            while stack:
                current_id = stack.pop()
                component.append(current_id)
                for neighbor_id in adjacency.get(current_id, set()):
                    if neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)
                    stack.append(neighbor_id)

            components.append(component)

        synthetic_layers: List[Layer] = []
        seen_signatures = set()

        for idx, component_ids in enumerate(components):
            if len(component_ids) < 2:
                continue

            component_layers = [by_id[layer_id] for layer_id in component_ids]
            if not self._is_strong_container_candidate(component_layers, bboxes):
                continue

            x1 = min(bboxes[layer_id][0] for layer_id in component_ids)
            y1 = min(bboxes[layer_id][1] for layer_id in component_ids)
            x2 = max(bboxes[layer_id][0] + bboxes[layer_id][2] for layer_id in component_ids)
            y2 = max(bboxes[layer_id][1] + bboxes[layer_id][3] for layer_id in component_ids)

            width = max(1.0, x2 - x1)
            height = max(1.0, y2 - y1)
            padding = max(8.0, min(18.0, min(width, height) * 0.08))

            geometry = GeometryBase(
                x=max(0.0, x1 - padding),
                y=max(0.0, y1 - padding),
                w=width + padding * 2,
                h=height + padding * 2,
            )

            signature = (
                round(geometry.x, 1),
                round(geometry.y, 1),
                round(geometry.w, 1),
                round(geometry.h, 1),
                tuple(sorted(component_ids)),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            synthetic_layers.append(
                Layer(
                    id=f"synthetic_container_{idx}",
                    type="container",
                    geometry=geometry,
                    content={
                        "editable": True,
                        "is_synthesized": True,
                        "synthesized_from": sorted(component_ids),
                        "nesting_role": "container",
                        "is_container": True,
                    },
                    style={
                        "stroke": "#64748b",
                        "strokeWidth": 1.5,
                        "fill": "rgba(255,255,255,0.0)",
                    },
                )
            )

        if not synthetic_layers:
            return layers

        combined = list(layers) + synthetic_layers
        order_lookup = {layer.id: idx for idx, layer in enumerate(layers)}
        order_lookup.update({layer.id: len(layers) + idx for idx, layer in enumerate(synthetic_layers)})
        combined.sort(key=lambda layer: (order_lookup.get(layer.id, 10**9), layer.geometry.y, layer.geometry.x))
        return combined

    def _looks_like_stacked_siblings(
        self,
        a: Tuple[float, float, float, float],
        b: Tuple[float, float, float, float],
    ) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b

        left = max(ax, bx)
        right = min(ax + aw, bx + bw)
        overlap_w = max(0.0, right - left)
        min_w = max(1.0, min(aw, bw))
        overlap_ratio = overlap_w / min_w

        center_delta = abs((ax + aw / 2) - (bx + bw / 2))
        width_ratio = min(aw, bw) / max(aw, bw)

        if ay <= by:
            vertical_gap = by - (ay + ah)
        else:
            vertical_gap = ay - (by + bh)

        return (
            overlap_ratio >= 0.35
            and center_delta <= max(aw, bw) * 0.25
            and width_ratio >= 0.55
            and -6.0 <= vertical_gap <= 36.0
        )

    def _is_strong_container_candidate(
        self,
        component_layers: List[Layer],
        bboxes: Dict[str, Tuple[float, float, float, float]],
    ) -> bool:
        if len(component_layers) < 2:
            return False

        widths = [bboxes[layer.id][2] for layer in component_layers]
        heights = [bboxes[layer.id][3] for layer in component_layers]
        x_centers = [bboxes[layer.id][0] + bboxes[layer.id][2] / 2 for layer in component_layers]

        width_spread = max(widths) / max(1e-6, min(widths))
        height_spread = max(heights) / max(1e-6, min(heights))
        center_spread = max(x_centers) - min(x_centers)

        union_left = min(bboxes[layer.id][0] for layer in component_layers)
        union_right = max(bboxes[layer.id][0] + bboxes[layer.id][2] for layer in component_layers)
        union_width = max(1.0, union_right - union_left)

        # Reject loose groups. We only want tight nested stacks.
        if width_spread > 1.9 and height_spread > 2.4:
            return False

        if center_spread > union_width * 0.35:
            return False

        # Require the group to be meaningfully stacked rather than just close.
        sorted_layers = sorted(component_layers, key=lambda layer: (bboxes[layer.id][1], bboxes[layer.id][0]))
        gaps = []
        for prev, cur in zip(sorted_layers, sorted_layers[1:]):
            px, py, pw, ph = bboxes[prev.id]
            cx, cy, cw, ch = bboxes[cur.id]
            gap = cy - (py + ph)
            gaps.append(gap)

        if not gaps:
            return False

        avg_gap = sum(gaps) / len(gaps)
        return avg_gap <= 24.0

    def _is_synthesized_container(self, layer: Layer) -> bool:
        content = layer.content if isinstance(layer.content, dict) else {}
        return bool(content.get("is_synthesized"))

    # ---------------------------------------------------------------------
    # Deterministic hierarchy inference
    # ---------------------------------------------------------------------

    def _build_hierarchy_metadata(self, layers: List[Layer]) -> List[Layer]:
        """
        Build a deterministic containment tree from geometry only.

        The rule is intentionally strict:
        - only box-like layers participate,
        - a parent must fully contain the child with a small margin,
        - the smallest enclosing parent becomes the immediate parent,
        - hierarchy metadata is stored in content without changing geometry.
        """
        if not layers:
            return layers

        candidates = [
            layer
            for layer in layers
            if layer.type in {"text", "shape", "container", "table"}
        ]

        if not candidates:
            return layers

        bbox_lookup: Dict[str, Tuple[float, float, float, float]] = {
            layer.id: self._layer_bbox(layer)
            for layer in candidates
        }

        parent_map: Dict[str, str] = {}
        children_map: Dict[str, List[str]] = {layer.id: [] for layer in candidates}

        for child in candidates:
            child_box = bbox_lookup[child.id]
            containing: List[Tuple[float, float, float, str, Layer]] = []

            for parent in candidates:
                if parent.id == child.id:
                    continue

                parent_box = bbox_lookup[parent.id]
                if not self._contains_bbox(parent_box, child_box):
                    continue

                area = parent_box[2] * parent_box[3]
                containing.append((area, parent_box[1], parent_box[0], parent.id, parent))

            if not containing:
                continue

            containing.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
            parent = containing[0][4]
            parent_map[child.id] = parent.id
            children_map.setdefault(parent.id, []).append(child.id)

        depth_cache: Dict[str, int] = {}

        def compute_depth(layer_id: str) -> int:
            if layer_id in depth_cache:
                return depth_cache[layer_id]
            parent_id = parent_map.get(layer_id)
            if not parent_id:
                depth_cache[layer_id] = 0
            else:
                depth_cache[layer_id] = compute_depth(parent_id) + 1
            return depth_cache[layer_id]

        for layer in candidates:
            compute_depth(layer.id)

        updated_layers: List[Layer] = []
        for layer in layers:
            cloned = copy.deepcopy(layer)

            if isinstance(cloned.content, dict):
                content = dict(cloned.content)
            else:
                content = {
                    "text": getattr(cloned.content, "text", ""),
                }

            child_ids = sorted(
                children_map.get(cloned.id, []),
                key=lambda child_id: (
                    bbox_lookup[child_id][1],
                    bbox_lookup[child_id][0],
                    child_id,
                ),
            )

            depth = depth_cache.get(cloned.id, 0)
            parent_id = parent_map.get(cloned.id)

            if parent_id:
                content["parent_id"] = parent_id
            else:
                content.pop("parent_id", None)

            content["children_ids"] = child_ids
            content["depth"] = depth
            content["is_container"] = bool(child_ids)

            if cloned.type == "text":
                if parent_id or content.get("synthesized_from"):
                    content["nesting_role"] = "node"
                elif child_ids:
                    content["nesting_role"] = "text_container"
                else:
                    content["nesting_role"] = "label"
            elif child_ids:
                content["nesting_role"] = "container"
            else:
                content["nesting_role"] = "node"

            cloned.content = content
            updated_layers.append(cloned)

        return updated_layers

    def _contains_bbox(
        self,
        outer: Tuple[float, float, float, float],
        inner: Tuple[float, float, float, float],
    ) -> bool:
        ox, oy, ow, oh = outer
        ix, iy, iw, ih = inner

        margin = max(2.0, min(8.0, min(ow, oh) * 0.03))

        return (
            ix >= ox + margin
            and iy >= oy + margin
            and ix + iw <= ox + ow - margin
            and iy + ih <= oy + oh - margin
        )

    def _resolve_connector_layer(
        self,
        layer: Layer,
        layers_by_id: Dict[str, Layer],
    ) -> Layer:
        """
        If a connector endpoint points to a text label, resolve it to the
        immediate enclosing block so arrows attach to the actual node.
        """
        current = layer
        visited = set()

        while current.id not in visited:
            visited.add(current.id)
            content = current.content if isinstance(current.content, dict) else {}
            parent_id = content.get("parent_id")
            if not parent_id:
                break

            parent = layers_by_id.get(str(parent_id))
            if not parent:
                break

            if current.type == "text":
                role = content.get("nesting_role")
                if role == "label":
                    current = parent
                    continue

            break

        return current

    # ---------------------------------------------------------------------
    # Candidate serialization
    # ---------------------------------------------------------------------

    def _layer_to_node_candidate(self, layer: Layer) -> Optional[Dict[str, Any]]:
        if layer.type not in {"text", "shape", "container", "table"}:
            return None

        text = ""
        if isinstance(layer.content, dict):
            text = str(layer.content.get("text", "")).strip()

        return {
            "id": layer.id,
            "type": layer.type,
            "text": text,
            "bbox": {
                "x": layer.geometry.x,
                "y": layer.geometry.y,
                "w": layer.geometry.w,
                "h": layer.geometry.h,
            },
        }

    # ---------------------------------------------------------------------
    # Multimodal connection extraction
    # ---------------------------------------------------------------------

    async def _extract_connections_from_image(
        self,
        image_path: str,
        layers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = f"""
You are analyzing a diagram image.

Return ONLY valid JSON.

TASK:
Infer only the connections/arrows between the already provided node candidates.

IMPORTANT RULES:
1. Do NOT invent boxes.
2. Do NOT modify node bounding boxes.
3. Do NOT return duplicate nodes.
4. Use only the exact node ids from the provided candidate list.
5. Preserve arrow direction exactly.

Known node candidates:
{json.dumps(layers, indent=2)}

RETURN FORMAT:
{{
  "connections": [
    {{
      "source_id": "node_id",
      "target_id": "node_id",
      "direction": "forward"
    }}
  ]
}}
"""

        data_url = self._image_to_data_url(image_path)

        raw_text = await self._call_multimodal_model(
            prompt=prompt,
            image_data_url=data_url,
        )

        payload = self._safe_json_loads(raw_text)
        return self._normalize_graph_payload(payload)

    async def _call_multimodal_model(
        self,
        prompt: str,
        image_data_url: str,
    ) -> str:
        client = AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.azure_api_key,
            api_version=self.azure_api_version,
        )

        messages = [
            {
                "role": "system",
                "content": "You extract diagram connections. Return ONLY JSON.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url,
                        },
                    },
                ],
            },
        ]

        try:
            response = await client.chat.completions.create(
                model=self.azure_deployment,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception:
            response = await client.chat.completions.create(
                model=self.azure_deployment,
                messages=messages,
                temperature=0,
            )

        return (response.choices[0].message.content or "{}").strip()

    def _normalize_graph_payload(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        connections = payload.get("connections", [])
        return {
            "connections": connections if isinstance(connections, list) else [],
        }

    def _safe_json_loads(
        self,
        text: str,
    ) -> Dict[str, Any]:
        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    def _image_to_data_url(self, image_path: str) -> str:
        suffix = Path(image_path).suffix.lower().lstrip(".")
        mime_map = {
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "png": "png",
            "webp": "webp",
        }

        mime = mime_map.get(suffix, "png")

        raw = Path(image_path).read_bytes()
        encoded = base64.b64encode(raw).decode("utf-8")

        return f"data:image/{mime};base64,{encoded}"

    # ---------------------------------------------------------------------
    # Connector creation
    # ---------------------------------------------------------------------

    def _build_connector_layers(
        self,
        graph: Dict[str, Any],
        layers_by_id: Dict[str, Layer],
    ) -> List[Layer]:
        connectors = []

        for idx, conn in enumerate(graph.get("connections", [])):
            source_id = str(conn.get("source_id", "")).strip()
            target_id = str(conn.get("target_id", "")).strip()

            if source_id not in layers_by_id or target_id not in layers_by_id:
                continue

            src = self._resolve_connector_layer(layers_by_id[source_id], layers_by_id)
            dst = self._resolve_connector_layer(layers_by_id[target_id], layers_by_id)

            source_anchor, target_anchor = self._determine_anchor_sides(src.geometry, dst.geometry)
            points = self._route_connector(
                src.geometry,
                dst.geometry,
                source_anchor=source_anchor,
                target_anchor=target_anchor,
                route_mode=str(conn.get("route_mode", "orthogonal")),
            )

            connectors.append(
                Layer(
                    id=f"connector_{idx}",
                    type="connector",
                    geometry=GeometryBase(
                        x=min(points[0], points[-2]),
                        y=min(points[1], points[-1]),
                        w=max(1, max(points[0::2]) - min(points[0::2])),
                        h=max(1, max(points[1::2]) - min(points[1::2])),
                    ),
                    content={
                        "points": points,
                        "endpoints": points,
                        "direction": "forward",
                        "style": "solid",
                        "route_mode": "orthogonal",
                        "source_layer_id": src.id,
                        "target_layer_id": dst.id,
                        "source_anchor": source_anchor,
                        "target_anchor": target_anchor,
                    },
                    style={
                        "stroke": "#ef4444",
                        "strokeWidth": 2,
                    },
                )
            )

        return connectors

    def _determine_anchor_sides(
        self,
        src: GeometryBase,
        dst: GeometryBase,
    ) -> Tuple[str, str]:
        sx = src.x + src.w / 2
        sy = src.y + src.h / 2
        tx = dst.x + dst.w / 2
        ty = dst.y + dst.h / 2

        dx = tx - sx
        dy = ty - sy

        if abs(dx) >= abs(dy):
            return ("right", "left") if dx >= 0 else ("left", "right")

        return ("bottom", "top") if dy >= 0 else ("top", "bottom")

    def _anchor_point(self, geom: GeometryBase, side: str) -> Tuple[float, float]:
        cx = geom.x + geom.w / 2
        cy = geom.y + geom.h / 2

        if side == "left":
            return (geom.x, cy)
        if side == "right":
            return (geom.x + geom.w, cy)
        if side == "top":
            return (cx, geom.y)
        if side == "bottom":
            return (cx, geom.y + geom.h)

        return (geom.x + geom.w, cy)

    def _route_connector(
        self,
        src: GeometryBase,
        dst: GeometryBase,
        source_anchor: str = "right",
        target_anchor: str = "left",
        route_mode: str = "orthogonal",
    ) -> List[float]:
        x1, y1 = self._anchor_point(src, source_anchor)
        x2, y2 = self._anchor_point(dst, target_anchor)

        if route_mode != "orthogonal":
            return [x1, y1, x2, y2]

        if abs(x2 - x1) >= abs(y2 - y1):
            mid_x = (x1 + x2) / 2
            return [x1, y1, mid_x, y1, mid_x, y2, x2, y2]

        mid_y = (y1 + y2) / 2
        return [x1, y1, x1, mid_y, x2, mid_y, x2, y2]


simple_level2_service = SimpleLevel2Service()
