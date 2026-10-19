from app.spec import SpecError, as_dict, as_list, as_text
from app.svgutil import esc, svg_document
from app.theme import THEME

_BANDS = (THEME["primary_soft"], THEME["lane"], "#FBF3E8")


def render_stack(spec: dict) -> tuple[str, list[str]]:
    layers = []
    for raw in as_list(spec.get("layers"), "layers"):
        layer = as_dict(raw, "layer")
        name = as_text(layer.get("name"))
        if not name:
            raise SpecError("Layer cần name")
        items = [_item(entry, name) for entry in as_list(layer.get("items"), "items")]
        if not items:
            raise SpecError(f"Layer '{name}' cần ít nhất một item")
        layers.append({"name": name, "items": items})
    if not layers:
        raise SpecError("Stack cần layers")
    if len(layers) > 10:
        raise SpecError("Stack giữ tối đa 10 layer")

    width = 1120
    label_w = 220
    content_x = label_w + 8
    content_w = width - content_x - 20
    laid = []
    height = 0
    gap = 10
    for index, layer in enumerate(layers):
        rows = _rows(layer["items"], content_w)
        band_h = max(72, 22 + len(rows) * 40)
        laid.append({**layer, "rows": rows, "height": band_h, "fill": _BANDS[index % len(_BANDS)]})
        height += band_h
    height += gap * (len(laid) - 1)

    parts = [f'<g font-family="{THEME["font_family"]}">']
    y = 0
    for layer in laid:
        parts.append(
            f'<rect x="0" y="{y:.2f}" width="{width}" height="{layer["height"]:.2f}" rx="12" '
            f'fill="{layer["fill"]}" stroke="{THEME["line"]}"/>'
        )
        parts.append(
            f'<rect x="12" y="{y + layer["height"] / 2 - 14:.2f}" width="4" height="28" rx="2" fill="{THEME["primary"]}"/>'
        )
        parts.append(
            f'<text x="28" y="{y + layer["height"] / 2 + 5:.2f}" font-size="15" font-weight="700" '
            f'fill="{THEME["primary"]}">{esc(layer["name"])}</text>'
        )
        rows_h = len(layer["rows"]) * 40
        row_y = y + (layer["height"] - rows_h) / 2
        for row_index, row in enumerate(layer["rows"]):
            cursor = content_x
            py = row_y + row_index * 40 + 6
            for item in row:
                stroke, fill = _pill(item["tone"])
                parts.append(
                    f'<rect x="{cursor:.2f}" y="{py:.2f}" width="{item["width"]:.2f}" height="28" rx="14" '
                    f'fill="{fill}" stroke="{stroke}"/>'
                )
                parts.append(
                    f'<text x="{cursor + item["width"] / 2:.2f}" y="{py + 18:.2f}" text-anchor="middle" '
                    f'font-size="12" fill="{THEME["ink"]}">{esc(item["label"])}</text>'
                )
                cursor += item["width"] + 8
        y += layer["height"] + gap
    parts.append("</g>")
    return svg_document(width, height, "".join(parts)), []


def _item(entry, layer_name: str) -> dict:
    if isinstance(entry, str):
        label, tone = entry.strip(), "primary"
    elif isinstance(entry, dict):
        label = as_text(entry.get("label"))
        tone = as_text(entry.get("tone") or "primary").lower()
    else:
        raise SpecError(f"Item trong layer '{layer_name}' phải là chuỗi hoặc object")
    if not label:
        raise SpecError(f"Item trong layer '{layer_name}' cần label")
    if tone not in {"primary", "accent", "done", "muted"}:
        raise SpecError("tone của item phải là primary, accent, done hoặc muted")
    return {"label": label, "tone": tone, "width": max(72, len(label) * 7.2 + 28)}


def _rows(items: list[dict], max_width: float) -> list[list[dict]]:
    rows: list[list[dict]] = [[]]
    used = 0
    for item in items:
        if rows[-1] and used + item["width"] > max_width:
            rows.append([])
            used = 0
        rows[-1].append(item)
        used += item["width"] + 8
    return rows


def _pill(tone: str) -> tuple[str, str]:
    if tone == "accent":
        return THEME["accent"], THEME["accent_soft"]
    if tone == "done":
        return THEME["done"], THEME["done_soft"]
    if tone == "muted":
        return THEME["faint"], THEME["paper"]
    return THEME["primary"], THEME["paper"]
