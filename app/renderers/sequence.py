from app.spec import SpecError, as_dict, as_list, as_text, require_id
from app.svgutil import esc, svg_document, wrap_words
from app.theme import THEME


def render_sequence(spec: dict) -> tuple[str, list[str]]:
    actors = []
    for raw in as_list(spec.get("actors"), "actors"):
        actor = as_dict(raw, "actor")
        actor_id = require_id(actor.get("id"), "id của actor")
        label = as_text(actor.get("label") or actor_id)
        kind = as_text(actor.get("kind") or "internal").lower()
        if kind not in {"internal", "external", "person"}:
            raise SpecError("kind của actor phải là internal, external hoặc person")
        if any(item["id"] == actor_id for item in actors):
            raise SpecError(f"Trùng actor '{actor_id}'")
        actors.append({"id": actor_id, "label": label, "kind": kind, "lines": wrap_words(label, 16)[:2] or [label]})
    if not actors:
        raise SpecError("Sequence cần actors")
    if len(actors) > 12:
        raise SpecError("Sequence giữ tối đa 12 actor")

    messages = []
    known = {actor["id"] for actor in actors}
    for raw in as_list(spec.get("messages"), "messages"):
        message = as_dict(raw, "message")
        source = as_text(message.get("from", message.get("source")))
        target = as_text(message.get("to", message.get("target")))
        if source not in known or target not in known:
            raise SpecError(f"Message tham chiếu actor không tồn tại: {source} → {target}")
        style = as_text(message.get("style") or "solid").lower()
        if style not in {"solid", "return", "dashed", "dotted", "bold"}:
            raise SpecError("style của message phải là solid, return, dashed, dotted hoặc bold")
        label = as_text(message.get("label"))
        if not label:
            raise SpecError("Message cần label")
        messages.append({"source": source, "target": target, "label": label, "style": style})
    if not messages:
        raise SpecError("Sequence cần messages")
    if len(messages) > 40:
        raise SpecError("Sequence giữ tối đa 40 message")

    box_w = 148
    col_w = 200
    margin = 36 + box_w / 2
    width = margin * 2 + col_w * (len(actors) - 1)
    width = max(width, 720)
    box_h = 54 if any(len(actor["lines"]) > 1 for actor in actors) else 40
    top = 8
    gap = 50
    msg_top = top + box_h + 28
    height = msg_top + max(len(messages) - 1, 0) * gap + 36
    xs = {actor["id"]: margin + index * col_w for index, actor in enumerate(actors)}
    bottom = height - 16

    parts = [
        f'<rect width="{width:.2f}" height="{height:.2f}" fill="{THEME["paper"]}"/>',
        "<defs>",
        f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{THEME["primary"]}"/></marker>',
        "</defs>",
        f'<g font-family="{THEME["font_family"]}">',
    ]
    for actor in actors:
        x = xs[actor["id"]]
        fill, stroke, text, dash = _actor_style(actor["kind"])
        parts.append(
            f'<rect x="{x - box_w / 2:.2f}" y="{top:.2f}" width="{box_w:.2f}" height="{box_h:.2f}" rx="8" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.4" {dash}/>'
        )
        block = len(actor["lines"]) * 15
        text_y = top + (box_h - block) / 2 + 12
        for index, line in enumerate(actor["lines"]):
            parts.append(
                f'<text x="{x:.2f}" y="{text_y + index * 15:.2f}" text-anchor="middle" font-size="13" '
                f'font-weight="700" fill="{text}">{esc(line)}</text>'
            )
        parts.append(
            f'<line x1="{x:.2f}" y1="{top + box_h:.2f}" x2="{x:.2f}" y2="{bottom:.2f}" '
            f'stroke="{THEME["faint"]}" stroke-dasharray="4 4"/>'
        )

    for index, message in enumerate(messages):
        y = msg_top + index * gap
        x1 = xs[message["source"]]
        x2 = xs[message["target"]]
        dashed = message["style"] in {"return", "dashed", "dotted"}
        width_stroke = "2.2" if message["style"] == "bold" else "1.5"
        color = THEME["edge"] if message["style"] == "return" else THEME["primary"]
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        if message["source"] == message["target"]:
            parts.append(
                f'<path d="M {x1:.2f} {y:.2f} h 28 v 22 H {x1:.2f}" fill="none" stroke="{color}" '
                f'stroke-width="{width_stroke}"{dash} marker-end="url(#arrow)"/>'
            )
            parts.append(
                f'<text x="{x1 + 34:.2f}" y="{y + 14:.2f}" font-size="12" fill="{THEME["ink"]}">{esc(message["label"])}</text>'
            )
            continue
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" stroke="{color}" '
            f'stroke-width="{width_stroke}"{dash} marker-end="url(#arrow)"/>'
        )
        label_w = max(16, len(message["label"]) * 6.6)
        mid = (x1 + x2) / 2
        parts.append(
            f'<rect x="{mid - label_w / 2:.2f}" y="{y - 18:.2f}" width="{label_w:.2f}" height="15" fill="{THEME["paper"]}"/>'
        )
        parts.append(
            f'<text x="{mid:.2f}" y="{y - 6:.2f}" text-anchor="middle" font-size="12" fill="{THEME["ink"]}">{esc(message["label"])}</text>'
        )
    parts.append("</g>")
    return svg_document(width, height, "".join(parts)), []


def _actor_style(kind: str) -> tuple[str, str, str, str]:
    if kind == "external":
        return THEME["paper"], THEME["accent"], THEME["ink"], 'stroke-dasharray="5 3"'
    if kind == "person":
        return THEME["primary_soft"], THEME["primary"], THEME["ink"], ""
    return THEME["primary"], THEME["primary"], "#FFFFFF", ""
