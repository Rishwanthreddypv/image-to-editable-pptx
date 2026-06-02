from typing import List, Optional, Dict
from app.schemas.layer import Layer, GeometryBase
from app.core.config import logger

class LayoutHierarchyService:
    def clean_hierarchy(self, containers: List[Layer], all_layers: List[Layer] = None) -> List[Layer]:
        """
        Refine the container tree by pruning duplicates, validating nesting,
        tightening boundaries, and removing structural noise.
        """
        if not containers:
            return []

        logger.info(f"Cleaning hierarchy for {len(containers)} containers")

        # 1. Deduplicate similar containers (IoU based)
        deduped = self._deduplicate(containers)
        
        # 2. Semantic Filtering: Remove decorative or giant swallowing regions
        filtered = self._filter_containers(deduped)

        # 3. Tighten boundaries around enclosed content (text, tables, graphics)
        tightened = self._tighten_boundaries(filtered, all_layers) if all_layers else filtered

        # 4. Global Child Assignment (Smallest Enclosing Container Logic)
        # This re-parents everything (including text/tables) to the BEST container.
        final_containers, final_content = self._assign_hierarchy(tightened, all_layers)
        
        # 5. Redundancy Collapsing: Remove containers with 0 or 1 child if they don't add value
        pruned = self._collapse_redundant_containers(final_containers, final_content)
        
        # 6. Rebuild final list and links
        result = self._rebuild_links(pruned)
        
        logger.info(f"Hierarchy cleaned: {len(containers)} -> {len(result)} containers")
        return result

    def _filter_containers(self, containers: List[Layer]) -> List[Layer]:
        """Reject tiny, extreme aspect ratio, giant swallowing, or UI_CHROME containers."""
        keep = []
        for c in containers:
            w, h = c.geometry.w, c.geometry.h
            area = w * h
            
            # Semantic filtering
            role = c.content.get('semantic_role', 'STRUCTURAL_CONTAINER')
            is_structural = c.content.get('is_structural', True)
            
            # 1. Reject UI Chrome (toolbars, sidebars belonging to the app)
            if role == 'UI_CHROME' or not is_structural:
                continue
                
            # 2. Reject Decorative elements
            if role == 'DECORATIVE':
                continue

            # 3. Reject giant boxes that cover > 95% of canvas (usually the background itself)
            if area > (1280 * 720 * 0.95):
                continue
                
            # 4. Reject tiny boxes (less than 40x40) unless they are semantic nodes
            if w < 40 and h < 40 and role != 'CONTENT_NODE':
                continue
                
            # Reject extremely thin lines
            if w < 10 or h < 10:
                continue
            
            # Confidence check
            confidence = c.content.get('confidence', 1.0)
            if confidence < 0.4:
                continue

            keep.append(c)
        return keep

    def _deduplicate(self, containers: List[Layer]) -> List[Layer]:
        """Aggressive IoU and Containment deduplication."""
        keep = []
        # Sort by area descending
        sorted_cont = sorted(containers, key=lambda l: l.geometry.w * l.geometry.h, reverse=True)
        
        for i, c1 in enumerate(sorted_cont):
            is_dup = False
            for c2 in keep:
                iou = self._calculate_iou(c1.geometry, c2.geometry)
                if iou > 0.8:
                    is_dup = True
                    break
                
                # If one is almost entirely contained in another and they have similar roles
                enclosure = self._calculate_enclosure_ratio(c1.geometry, c2.geometry)
                if enclosure > 0.95 and c1.content.get('semantic_role') == c2.content.get('semantic_role'):
                    is_dup = True
                    break
                    
            if not is_dup:
                keep.append(c1)
        return keep

    def _assign_hierarchy(self, containers: List[Layer], all_layers: List[Layer]):
        """Assign every layer to the SMALLEST STRUCTURAL_CONTAINER that fully encloses it."""
        if not all_layers:
            return containers, []

        content_layers = [l for l in all_layers if l.type != "container"]
        
        # Reset current parentage
        for l in content_layers:
            l.parent_group_id = None
        for c in containers:
            c.parent_group_id = None
            c.child_layer_ids = []

        # Only STRUCTURAL_CONTAINER or TABLE can be parents
        potential_parents = [c for c in containers if c.content.get('semantic_role') in ['STRUCTURAL_CONTAINER', 'TABLE']]

        # 1. Assign content to smallest valid container
        for layer in content_layers:
            best_parent = None
            min_area = float('inf')
            
            for container in potential_parents:
                enclosure = self._calculate_enclosure_ratio(layer.geometry, container.geometry)
                if enclosure > 0.85:
                    area = container.geometry.w * container.geometry.h
                    if area < min_area:
                        min_area = area
                        best_parent = container
            
            if best_parent:
                layer.parent_group_id = best_parent.id
                best_parent.child_layer_ids.append(layer.id)

        # 2. Build Container-to-Container hierarchy
        for child in containers:
            best_parent = None
            min_area = float('inf')
            child_area = child.geometry.w * child.geometry.h
            
            for parent in potential_parents:
                if child.id == parent.id: continue
                
                parent_area = parent.geometry.w * parent.geometry.h
                if parent_area <= child_area: continue
                
                enclosure = self._calculate_enclosure_ratio(child.geometry, parent.geometry)
                if enclosure > 0.85:
                    if parent_area < min_area:
                        min_area = parent_area
                        best_parent = parent
            
            if best_parent:
                child.parent_group_id = best_parent.id
                best_parent.child_layer_ids.append(child.id)

        return containers, content_layers

    def _collapse_redundant_containers(self, containers: List[Layer], content_layers: List[Layer]) -> List[Layer]:
        """Remove containers that don't add semantic value (0 children or redundant single-child wrappers)."""
        keep = []
        for c in containers:
            role = c.content.get('semantic_role')
            
            # Always keep CONTENT_NODE as they are atomic entities
            if role == 'CONTENT_NODE':
                keep.append(c)
                continue

            direct_children_count = len(c.child_layer_ids)
            
            # Keep if it has multiple children
            if direct_children_count > 1:
                keep.append(c)
                continue
                
            # Keep single-child containers ONLY if they have specific semantic importance
            label = c.content.get('label', '').lower()
            is_important = any(kw in label for kw in ['card', 'panel', 'module', 'system'])
            
            if direct_children_count == 1 and is_important:
                keep.append(c)
                continue
            
            # Otherwise, orphan the child and prune this container
            if direct_children_count == 1:
                child_id = c.child_layer_ids[0]
                child = next((l for l in containers + content_layers if l.id == child_id), None)
                if child:
                    child.parent_group_id = c.parent_group_id
                    continue
            
            # Prune empty containers unless they are CONTENT_NODE (already handled)
            if direct_children_count == 0:
                continue
                
        return keep

    def _tighten_boundaries(self, containers: List[Layer], all_layers: List[Layer]) -> List[Layer]:
        """Shrink container bounding boxes to the union of their enclosed elements."""
        refined = []
        PADDING = 8

        for container in containers:
            enclosed_elements = [
                l for l in all_layers 
                if l.type != "container" and self._calculate_enclosure_ratio(l.geometry, container.geometry) > 0.85
            ]

            if not enclosed_elements:
                refined.append(container)
                continue

            min_x = min(e.geometry.x for e in enclosed_elements)
            min_y = min(e.geometry.y for e in enclosed_elements)
            max_r = max(e.geometry.x + e.geometry.w for e in enclosed_elements)
            max_b = max(e.geometry.y + e.geometry.h for e in enclosed_elements)

            new_x = max(container.geometry.x, min_x - PADDING)
            new_y = max(container.geometry.y, min_y - PADDING)
            new_w = min(container.geometry.w + (container.geometry.x - new_x), (max_r - min_x) + 2 * PADDING)
            new_h = min(container.geometry.h + (container.geometry.y - new_y), (max_b - min_y) + 2 * PADDING)

            container.geometry = GeometryBase(x=new_x, y=new_y, w=new_w, h=new_h)
            refined.append(container)

        return refined

    def _rebuild_links(self, containers: List[Layer]) -> List[Layer]:
        # Sort so we return consistent order
        return sorted(containers, key=lambda l: (l.geometry.y, l.geometry.x))

    def _calculate_iou(self, g1: GeometryBase, g2: GeometryBase) -> float:
        intersection = self._calculate_intersection(g1, g2)
        area1 = g1.w * g1.h
        area2 = g2.w * g2.h
        union = area1 + area2 - intersection
        if union <= 0: return 0
        return intersection / union

    def _calculate_enclosure_ratio(self, inner: GeometryBase, outer: GeometryBase) -> float:
        intersection = self._calculate_intersection(inner, outer)
        inner_area = inner.w * inner.h
        if inner_area <= 0: return 0
        return intersection / inner_area

    def _calculate_intersection(self, g1: GeometryBase, g2: GeometryBase) -> float:
        dx = min(g1.x + g1.w, g2.x + g2.w) - max(g1.x, g2.x)
        dy = min(g1.y + g1.h, g2.y + g2.h) - max(g1.y, g2.y)
        if dx > 0 and dy > 0:
            return dx * dy
        return 0

layout_hierarchy_service = LayoutHierarchyService()
