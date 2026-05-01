# Grafana Canvas Panel Guide

Hard-won lessons from building the network topology canvas panel in this demo.

## Connection Coordinate System

The connection anchor y-axis is **inverted** from screen coordinates:

| Value | Meaning |
|-------|---------|
| `y: 1` | **TOP** edge of the element |
| `y: -1` | **BOTTOM** edge of the element |
| `x: -1` | Left edge |
| `x: 1` | Right edge |
| `0` | Center (on either axis) |

For a downward-flowing connection (parent → child):
```json
"source": { "x": 0, "y": -1.0 },
"target": { "x": 0, "y": 1.0 }
```

For a horizontal connection (left → right):
```json
"source": { "x": 1.0, "y": 0 },
"target": { "x": -1.0, "y": 0 }
```

Getting the y-axis backwards makes arrows overshoot or point in the wrong direction. The x-axis is intuitive (negative = left, positive = right).

## Element Positioning

Canvas elements use absolute pixel coordinates (`left`, `top`, `width`, `height`). The canvas renders at whatever pixel width the panel occupies on screen.

### Panel width estimates

| `gridPos.w` (out of 24) | Approximate pixel width |
|--------------------------|------------------------|
| 24 | 1100–1200px |
| 14 | 650–850px |
| 12 | 550–700px |
| 8 | 350–500px |

### Don't scale — rebuild

If you need to resize a canvas layout (e.g., shrinking from `w=24` to `w=14`), **do not multiply all positions by a scale factor**. This crushes icons and leaves dead space. Rebuild positions from scratch for the target width.

## Icon Sizing

Validated sizes for a `w=14` topology panel (~850px wide):

| Element | Size |
|---------|------|
| Internet/cloud icon | 65–75px |
| Primary devices (routers) | 45–50px |
| Secondary devices (LBs, dist switches) | 50–55px |
| Tertiary devices (access switches) | 44–48px |
| Pool/server icons | 42–48px |

When resizing, keep icons centered at the same midpoint:
```python
new_left = old_left + (old_width - new_width) / 2
new_top = old_top + (old_height - new_height) / 2
```

## External SVG Icons

Canvas icons support external URLs. Use `"mode": "fixed"` (**not** `"mode": "resource"`):

```json
"config": {
    "path": {
        "fixed": "https://storage.googleapis.com/your-bucket/icon.svg",
        "mode": "fixed"
    }
}
```

### Requirements
- Host must serve CORS headers (`Access-Control-Allow-Origin: *`)
- SVGs with deeply nested `<g transform>` elements may not render — use simpler SVGs
- `raw.githubusercontent.com` is blocked by Grafana Cloud CSP — use GCS or similar
- Base64 data URIs (`data:image/svg+xml;base64,...`) also do not work
- Multi-color SVGs with hardcoded fills render their own colors (the canvas `fill` override won't apply)

### CORS setup for GCS
```bash
echo '[{"origin":["*"],"method":["GET","HEAD"],"responseHeader":["Content-Type"],"maxAgeSeconds":3600}]' > cors.json
gsutil cors set cors.json gs://your-bucket
```

## Python Generation Pattern

Editing 30+ canvas elements by hand in JSON is error-prone. Use helper functions:

```python
def icon_el(name, left, top, w, h, svg, fill="#73BF69", field=""):
    return {
        "type": "icon", "name": name,
        "placement": {"left": left, "top": top, "width": w, "height": h},
        "background": {"color": {"fixed": "transparent"}},
        "border": {"color": {"fixed": "transparent"}, "width": 0},
        "constraint": {"horizontal": "left", "vertical": "top"},
        "config": {
            "path": {"fixed": svg, "mode": "fixed"},
            "fill": {"fixed": fill, "field": field}
        },
        "connections": []
    }

def text_el(name, left, top, w, h, txt, size=10, color="#FFFFFF", align="center"):
    return {
        "type": "text", "name": name,
        "placement": {"left": left, "top": top, "width": w, "height": h},
        "background": {"color": {"fixed": "transparent"}},
        "border": {"color": {"fixed": "transparent"}, "width": 0},
        "constraint": {"horizontal": "left", "vertical": "top"},
        "config": {
            "align": align, "valign": "middle",
            "color": {"fixed": color},
            "size": size,
            "text": {"fixed": txt, "mode": "fixed"}
        },
        "connections": []
    }

def conn(target, sx, sy, tx, ty, color="rgba(204,204,220,0.35)",
         style="dotted", direction="forward", size=1.5):
    return {
        "targetName": target,
        "color": {"fixed": color},
        "size": {"fixed": size, "min": 1, "max": 10},
        "path": "straight",
        "lineStyle": {"animate": True, "style": style},
        "direction": {"fixed": direction, "mode": "fixed"},
        "source": {"x": sx, "y": sy},
        "sourceOriginal": {"x": 0, "y": 0},
        "target": {"x": tx, "y": ty},
        "targetOriginal": {"x": 0, "y": 0},
        "vertices": []
    }
```

Build elements in a list, inject into the dashboard JSON, push via API.

## Dashboard API Push

```bash
curl -s -X POST "https://your-instance.grafana.net/api/dashboards/db" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

- The JSON must include `"uid": "your-uid"` and `"overwrite": true` to update in place
- Without a UID, each push creates a new dashboard
- Use the `glsa_` service account token, not the `glc_` cloud access policy token

## Other Gotchas

| Issue | Fix |
|-------|-----|
| Text panel doesn't render inline SVG | Use emoji or plain text instead |
| Stat panels show PromQL expression | Set `"textMode": "value"` not `"value_and_name"` |
| Animated dotted lines need `lineStyle.animate: true` | Also set `"style": "dotted"` or `"dashed"` |
| Data-driven icon fill shows no icon when field has no data | Set a `"fixed"` fallback color alongside the `"field"` binding |
| Canvas panel title overlaps with internal title element | Set the panel `"title": ""` (empty) and use a text element inside the canvas instead |
