import base64
import re
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.spec import SpecError, as_text
from app.theme import FRAME_WIDTH, THEME, TYPE_LABELS

_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def esc(value) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def wrap_words(text: str, limit: int) -> list[str]:
    words = as_text(text).split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and len(trial) > limit:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def svg_document(width: float, height: float, body: str) -> str:
    family = THEME["font_family"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="{height:.2f}" '
        f'viewBox="0 0 {width:.2f} {height:.2f}" font-family="{family}">{body}</svg>'
    )


def embed_images(svg: str, extra_dirs: list[Path] | None = None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    cache: dict[Path, str] = {}

    def replace(match: re.Match) -> str:
        attr, href = match.group(1), match.group(2)
        if href.startswith("data:"):
            return match.group(0)
        path = _resolve_image(_xml_unescape(href), extra_dirs or [])
        if path is None:
            if Path(href).suffix.lower() in _MIME:
                warnings.append(f"Không nhúng được ảnh: {href}")
            return match.group(0)
        if path not in cache:
            mime = _MIME[path.suffix.lower()]
            cache[path] = "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        return f'{attr}="{cache[path]}"'

    return re.sub(r'\b((?:xlink:)?href)\s*=\s*"([^"]+)"', replace, svg), warnings


def frame_svg(raw_svg: str, spec: dict) -> str:
    inner, view_box, width, height = _extract_svg(raw_svg)
    if width <= 0 or height <= 0:
        raise SpecError("SVG kết xuất không có kích thước")

    max_width = 1120
    min_width = 640
    if width > max_width:
        scale = max_width / width
    elif width < min_width:
        scale = min_width / width
    else:
        scale = 1
    draw_w = width * scale
    draw_h = height * scale
    draw_x = (FRAME_WIDTH - draw_w) / 2

    title = " ".join(as_text(spec.get("title")).split())
    subtitle = " ".join(as_text(spec.get("subtitle")).split())
    footer = " ".join(as_text(spec.get("footer")).split()) or THEME["footer"]
    caption_lines = wrap_words(as_text(spec.get("caption")), 110)[:6]
    kind = as_text(spec.get("type")).lower()
    chip = TYPE_LABELS.get(kind, kind.upper() or "DIAGRAM")
    title_size = 22 if len(title) <= 52 else 18 if len(title) <= 78 else 16

    title_y = 42
    if subtitle:
        rule_y = title_y + 36
    else:
        rule_y = title_y + 16
    content_top = rule_y + 16
    cursor = content_top + draw_h
    caption_y = cursor + 18
    if caption_lines:
        cursor = caption_y + (len(caption_lines) - 1) * 16
    footer_rule = cursor + 14
    footer_y = footer_rule + 20
    total_h = footer_y + 16

    font = THEME["font_family"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{FRAME_WIDTH}" height="{total_h:.2f}" viewBox="0 0 {FRAME_WIDTH} {total_h:.2f}" '
        f'font-family="{font}" text-rendering="optimizeLegibility">',
        f'<rect width="{FRAME_WIDTH}" height="{total_h:.2f}" fill="{THEME["paper"]}"/>',
        f'<rect width="{FRAME_WIDTH}" height="5" fill="{THEME["primary"]}"/>',
        f'<rect x="1032" y="22" width="132" height="22" rx="11" fill="{THEME["primary_soft"]}"/>',
        f'<text x="1098" y="37" text-anchor="middle" font-size="10" font-weight="700" '
        f'fill="{THEME["primary"]}" letter-spacing="0.08em">{esc(chip)}</text>',
        f'<text x="36" y="{title_y}" font-size="{title_size}" font-weight="700" fill="{THEME["ink"]}">{esc(title)}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="36" y="{title_y + 22}" font-size="13" fill="{THEME["muted"]}">{esc(subtitle)}</text>'
        )
    parts.append(
        f'<line x1="36" y1="{rule_y}" x2="1164" y2="{rule_y}" stroke="{THEME["line"]}"/>'
    )
    parts.append(
        f'<svg x="{draw_x:.2f}" y="{content_top:.2f}" width="{draw_w:.2f}" height="{draw_h:.2f}" '
        f'viewBox="{esc(view_box)}" overflow="hidden">{inner}</svg>'
    )
    for index, line in enumerate(caption_lines):
        parts.append(
            f'<text x="36" y="{caption_y + index * 16}" font-size="12" fill="{THEME["muted"]}">{esc(line)}</text>'
        )
    parts.append(
        f'<line x1="36" y1="{footer_rule}" x2="1164" y2="{footer_rule}" stroke="{THEME["line"]}"/>'
    )
    parts.append(
        f'<text x="36" y="{footer_y}" font-size="11" fill="{THEME["muted"]}">{esc(footer)}</text>'
    )
    parts.append(
        f'<rect x="0.5" y="0.5" width="{FRAME_WIDTH - 1}" height="{total_h - 1:.2f}" '
        f'fill="none" stroke="{THEME["line"]}"/>'
    )
    parts.append("</svg>")
    return _uniquify_ids("".join(parts))


def _extract_svg(svg: str) -> tuple[str, str, float, float]:
    svg = svg.strip()
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg, count=1)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg, count=1)
    svg = svg.replace("<ns0:", "<").replace("</ns0:", "</")
    svg = svg.replace('xmlns:ns0="http://www.w3.org/2000/svg"', 'xmlns="http://www.w3.org/2000/svg"')
    match = re.search(r"<svg\b([^>]*)>", svg, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise SpecError("Renderer không trả về SVG")
    end = svg.rfind("</svg>")
    if end < match.end():
        raise SpecError("SVG không hợp lệ")
    inner = svg[match.end():end].strip()
    attrs = match.group(1)
    view_box = _attr(attrs, "viewBox")
    if view_box:
        parts = [float(item) for item in view_box.replace(",", " ").split()]
        if len(parts) != 4:
            raise SpecError("viewBox của SVG không hợp lệ")
        return inner, view_box, parts[2], parts[3]
    width = _length(attrs, "width")
    height = _length(attrs, "height")
    return inner, f"0 0 {width:.2f} {height:.2f}", width, height


def _attr(attrs: str, name: str) -> str:
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs)
    return match.group(1) if match else ""


def _length(attrs: str, name: str) -> float:
    raw = _attr(attrs, name)
    match = re.match(r"([0-9.]+)", raw)
    if not match:
        raise SpecError(f"SVG thiếu {name}")
    return float(match.group(1))


def _uniquify_ids(svg: str) -> str:
    prefix = "f" + uuid.uuid4().hex[:8] + "_"
    ids = sorted(set(re.findall(r'\bid="([^"]+)"', svg)), key=len, reverse=True)
    for ident in ids:
        escaped = re.escape(ident)
        svg = re.sub(rf'\bid="{escaped}"', f'id="{prefix}{ident}"', svg)
        svg = re.sub(rf"url\('#{escaped}'\)", f"url('#{prefix}{ident}')", svg)
        svg = re.sub(rf'url\("#{escaped}"\)', f'url(#{prefix}{ident})', svg)
        svg = re.sub(rf"url\(#{escaped}\)", f"url(#{prefix}{ident})", svg)
        svg = re.sub(rf'(xlink:href|href)="#{escaped}"', rf'\1="#{prefix}{ident}"', svg)
    return svg


def _resolve_image(href: str, extra_dirs: list[Path]) -> Path | None:
    href = href.strip()
    if not href or href.startswith("data:"):
        return None
    candidates: list[Path] = []
    if href.startswith("file:"):
        raw = unquote(urlparse(href).path)
        if re.match(r"^/[A-Za-z]:", raw):
            raw = raw[1:]
        candidates.append(Path(raw))
    else:
        candidates.append(Path(unquote(href)))
    for folder in extra_dirs:
        candidates.append(folder / href)
        candidates.append(folder / Path(href).name)
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.suffix.lower() in _MIME and candidate.stat().st_size <= 5_000_000:
                return candidate
        except OSError:
            continue
    return None


def _xml_unescape(text: str) -> str:
    return (
        text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
        .replace("&amp;", "&")
    )
