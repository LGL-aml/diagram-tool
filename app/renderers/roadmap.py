from app.spec import SpecError, as_dict, as_list, as_text, month_index, months_between, parse_mark
from app.svgutil import esc, svg_document, wrap_words
from app.theme import THEME

_STATUS = {
    "done": (THEME["done"], "#FFFFFF", "Đã xong"),
    "active": (THEME["primary"], "#FFFFFF", "Đang làm"),
    "planned": (THEME["lane"], THEME["ink"], "Kế hoạch"),
    "risk": (THEME["risk"], "#FFFFFF", "Rủi ro"),
}
_STATUS_EN = {
    "done": "Done",
    "active": "Active",
    "planned": "Planned",
    "risk": "Risk",
}
_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_roadmap(spec: dict) -> tuple[str, list[str]]:
    lanes = as_list(spec.get("lanes"), "lanes")
    if not lanes:
        raise SpecError("Roadmap cần ít nhất một lane")
    if len(lanes) > 12:
        raise SpecError("Roadmap giữ tối đa 12 lane")

    parsed = []
    marks = []
    for raw_lane in lanes:
        lane = as_dict(raw_lane, "lane")
        name = as_text(lane.get("name"))
        if not name:
            raise SpecError("Lane cần name")
        items = []
        for raw_item in as_list(lane.get("items"), "items"):
            item = as_dict(raw_item, "hạng mục")
            label = as_text(item.get("label"))
            if not label:
                raise SpecError(f"Hạng mục trong lane '{name}' cần label")
            status = as_text(item.get("status") or "planned").lower()
            if status not in _STATUS:
                raise SpecError("status phải là done, active, planned hoặc risk")
            start = parse_mark(item.get("start"), "start")
            end = parse_mark(item.get("end"), "end")
            if (end.year, end.month) < (start.year, start.month):
                raise SpecError(f"Hạng mục '{label}' có end trước start")
            items.append({"label": label, "status": status, "start": start, "end": end})
            marks.extend((start, end))
        parsed.append({"name": name, "items": items})

    milestones = []
    for raw in as_list(spec.get("milestones"), "milestones"):
        item = as_dict(raw, "milestone")
        label = as_text(item.get("label"))
        if not label:
            raise SpecError("Milestone cần label")
        mark = parse_mark(item.get("at"), "point")
        milestones.append({"label": label, "at": mark})
        marks.append(mark)

    if len(marks) > 80:
        raise SpecError("Roadmap giữ tối đa 80 hạng mục và milestone")

    start, end = _range(spec, marks)
    months = months_between(start, end)
    for lane in parsed:
        for item in lane["items"]:
            item["start_index"] = month_index(months, item["start"], f"Start của '{item['label']}'")
            item["end_index"] = month_index(months, item["end"], f"End của '{item['label']}'")
    for item in milestones:
        item["index"] = month_index(months, item["at"], f"Milestone '{item['label']}'")

    today = None
    if spec.get("today") not in (None, ""):
        today_mark = parse_mark(spec.get("today"), "point")
        today = month_index(months, today_mark, "today")

    count = len(months)
    col_w = 68 if count <= 12 else 50 if count <= 24 else 36
    label_w = 176
    packed = []
    outside = 16
    for lane in parsed:
        rows, row_count = _pack(lane["items"])
        name_lines = wrap_words(lane["name"], 18) or [lane["name"]]
        lane_h = max(len(name_lines) * 16 + 20, row_count * 36 + 16, 52)
        for row, item in rows:
            bar_w = max(10, (item["end_index"] - item["start_index"] + 1) * col_w - 8)
            if len(item["label"]) * 6.4 > bar_w - 14:
                outside = max(outside, len(item["label"]) * 6.5 + 18)
        packed.append({"name": lane["name"], "lines": name_lines, "rows": rows, "row_count": row_count, "height": lane_h})

    grid_right = label_w + col_w * count
    for item in milestones:
        center = label_w + (item["index"] + 0.5) * col_w
        half = len(item["label"]) * 6.8 / 2
        outside = max(outside, center + half + 18 - grid_right)

    english = as_text(spec.get("locale")).lower() == "en"
    status_names = _STATUS_EN if english else {key: value[2] for key, value in _STATUS.items()}
    today_label = "Today" if english else "Hôm nay"
    month_names = _MONTHS_EN if english else None

    multi = months[0].year != months[-1].year
    milestone_h = 58 if milestones else 8
    header_h = 44 if multi else 30
    grid_top = milestone_h + header_h
    width = label_w + col_w * count + outside
    body_h = sum(item["height"] for item in packed)
    legend_h = 36
    height = grid_top + body_h + legend_h + 8

    parts = [
        f'<rect width="{width:.2f}" height="{height:.2f}" fill="{THEME["paper"]}"/>',
        '<g font-family="' + THEME["font_family"] + '">',
    ]

    y = grid_top
    for index, lane in enumerate(packed):
        fill = THEME["paper"] if index % 2 == 0 else THEME["lane"]
        parts.append(
            f'<rect x="0" y="{y:.2f}" width="{width:.2f}" height="{lane["height"]:.2f}" fill="{fill}"/>'
        )
        if today is not None:
            band_x = label_w + today * col_w
            parts.append(
                f'<rect x="{band_x:.2f}" y="{y:.2f}" width="{col_w:.2f}" height="{lane["height"]:.2f}" '
                f'fill="{THEME["accent"]}" opacity="0.22"/>'
            )
        name_top = y + (lane["height"] - len(lane["lines"]) * 16) / 2 + 12
        for line_index, line in enumerate(lane["lines"]):
            parts.append(
                f'<text x="16" y="{name_top + line_index * 16:.2f}" font-size="13" font-weight="700" '
                f'fill="{THEME["ink"]}">{esc(line)}</text>'
            )
        inner_top = y + (lane["height"] - lane["row_count"] * 36) / 2
        for row, item in lane["rows"]:
            bar_x = label_w + item["start_index"] * col_w + 4
            bar_w = max(10, (item["end_index"] - item["start_index"] + 1) * col_w - 8)
            bar_y = inner_top + row * 36 + 7
            color, text_color, _label = _STATUS[item["status"]]
            stroke = THEME["faint"] if item["status"] == "planned" else color
            parts.append(f'<g><title>{esc(item["label"])}</title>')
            parts.append(
                f'<rect x="{bar_x:.2f}" y="{bar_y:.2f}" width="{bar_w:.2f}" height="22" rx="6" '
                f'fill="{color}" stroke="{stroke}"/>'
            )
            inside = len(item["label"]) * 6.4 <= bar_w - 14
            if inside:
                parts.append(
                    f'<text x="{bar_x + 8:.2f}" y="{bar_y + 15:.2f}" font-size="11" fill="{text_color}">{esc(item["label"])}</text>'
                )
            else:
                parts.append(
                    f'<text x="{bar_x + bar_w + 6:.2f}" y="{bar_y + 15:.2f}" font-size="11" fill="{THEME["ink"]}">{esc(item["label"])}</text>'
                )
            parts.append("</g>")
        parts.append(
            f'<line x1="0" y1="{y + lane["height"]:.2f}" x2="{width:.2f}" y2="{y + lane["height"]:.2f}" stroke="{THEME["line"]}"/>'
        )
        y += lane["height"]

    for index, month in enumerate(months):
        x = label_w + index * col_w
        strong = month.month in {1, 4, 7, 10}
        parts.append(
            f'<line x1="{x:.2f}" y1="{grid_top:.2f}" x2="{x:.2f}" y2="{grid_top + body_h:.2f}" '
            f'stroke="{THEME["line"]}" stroke-width="{"1.4" if strong else "1"}"/>'
        )
        label_x = x + col_w / 2
        parts.append(
            f'<text x="{label_x:.2f}" y="{milestone_h + 18:.2f}" text-anchor="middle" font-size="11" '
            f'fill="{THEME["muted"]}">{month_names[month.month - 1] if month_names else f"T{month.month}"}</text>'
        )
        if multi and month.month == 1:
            parts.append(
                f'<text x="{label_x:.2f}" y="{milestone_h + 32:.2f}" text-anchor="middle" font-size="10" '
                f'fill="{THEME["faint"]}">{month.year}</text>'
            )
    if not multi:
        parts.append(
            f'<text x="{label_w - 12:.2f}" y="{milestone_h + 18:.2f}" text-anchor="end" font-size="12" '
            f'font-weight="700" fill="{THEME["ink"]}">{months[0].year}</text>'
        )
    parts.append(
        f'<line x1="{label_w:.2f}" y1="{grid_top:.2f}" x2="{label_w + col_w * count:.2f}" y2="{grid_top:.2f}" '
        f'stroke="{THEME["faint"]}"/>'
    )
    if today is not None:
        line_x = label_w + (today + 0.5) * col_w
        parts.append(
            f'<line x1="{line_x:.2f}" y1="{milestone_h:.2f}" x2="{line_x:.2f}" y2="{grid_top + body_h:.2f}" '
            f'stroke="{THEME["accent"]}" stroke-width="1.6"/>'
        )

    last_right = -10_000.0
    for item in milestones:
        center = label_w + (item["index"] + 0.5) * col_w
        label_w_est = len(item["label"]) * 6.8
        center = min(max(center, label_w_est / 2 + 8), width - label_w_est / 2 - 8)
        left = center - label_w_est / 2
        below = left < last_right + 8
        diamond_y = 30
        parts.append(
            f'<path d="M {center:.2f} {diamond_y - 6} L {center + 6:.2f} {diamond_y} '
            f'L {center:.2f} {diamond_y + 6} L {center - 6:.2f} {diamond_y} Z" fill="{THEME["accent"]}"/>'
        )
        text_y = 48 if below else 16
        parts.append(
            f'<text x="{center:.2f}" y="{text_y}" text-anchor="middle" font-size="11" font-weight="700" '
            f'fill="{THEME["accent"]}">{esc(item["label"])}</text>'
        )
        last_right = max(last_right, center + label_w_est / 2)

    legend_y = grid_top + body_h + 22
    cursor = 16
    for key in ("done", "active", "planned", "risk"):
        color, _text, _default = _STATUS[key]
        label = status_names[key]
        stroke = THEME["faint"] if key == "planned" else color
        parts.append(
            f'<rect x="{cursor:.2f}" y="{legend_y - 10:.2f}" width="12" height="12" rx="3" fill="{color}" stroke="{stroke}"/>'
        )
        parts.append(
            f'<text x="{cursor + 18:.2f}" y="{legend_y:.2f}" font-size="12" fill="{THEME["muted"]}">{label}</text>'
        )
        cursor += 18 + len(label) * 7 + 18
    if today is not None:
        parts.append(
            f'<rect x="{cursor:.2f}" y="{legend_y - 10:.2f}" width="12" height="12" rx="2" '
            f'fill="{THEME["accent"]}" opacity="0.7"/>'
        )
        parts.append(
            f'<text x="{cursor + 18:.2f}" y="{legend_y:.2f}" font-size="12" fill="{THEME["muted"]}">{today_label}</text>'
        )
    parts.append("</g>")
    return svg_document(width, height, "".join(parts)), []


def _range(spec: dict, marks: list) -> tuple:
    raw_range = spec.get("range") if isinstance(spec.get("range"), dict) else {}
    start_raw = spec.get("start", raw_range.get("start"))
    end_raw = spec.get("end", raw_range.get("end"))
    if start_raw or end_raw:
        if not start_raw or not end_raw:
            raise SpecError("Roadmap cần cả start và end, hoặc bỏ trống để tự tính")
        return parse_mark(start_raw, "start"), parse_mark(end_raw, "end")
    if not marks:
        raise SpecError("Roadmap chưa có mốc thời gian")
    return min(marks), max(marks)


def _pack(items: list[dict]) -> tuple[list[tuple[int, dict]], int]:
    if not items:
        return [], 1
    row_ends: list[int] = []
    placed = []
    for item in sorted(items, key=lambda entry: (entry["start_index"], entry["end_index"])):
        row = next((index for index, end in enumerate(row_ends) if item["start_index"] > end), None)
        if row is None:
            row = len(row_ends)
            row_ends.append(item["end_index"])
        else:
            row_ends[row] = item["end_index"]
        placed.append((row, item))
    return placed, len(row_ends)
