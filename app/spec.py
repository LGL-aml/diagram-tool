import json
import re
from datetime import date, datetime

import yaml

from app.theme import THEME, TONES

class SpecError(ValueError):
    pass


_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,64}$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def as_list(value, name: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError(f"{name} phải là danh sách")
    return value


def as_dict(value, name: str) -> dict:
    if not isinstance(value, dict):
        raise SpecError(f"{name} phải là object")
    return value


def require_id(value, label: str = "id") -> str:
    text = as_text(value)
    if not _ID.match(text):
        raise SpecError(f"{label} phải bắt đầu bằng chữ và chỉ gồm chữ, số, _ hoặc -")
    return text


def safe_name(value: str) -> str:
    text = as_text(value)
    if not _NAME.match(text):
        raise SpecError("Tên file chỉ gồm chữ, số, _ và -, và phải bắt đầu bằng chữ hoặc số")
    return text


def resolve_color(value, default: str | None = None) -> str:
    if value is None or as_text(value) == "":
        if default is None:
            raise SpecError("Thiếu màu")
        return default
    text = as_text(value)
    tone = TONES.get(text.lower())
    if tone:
        return tone
    if _HEX.match(text):
        return text
    known = ", ".join(TONES)
    raise SpecError(f"Màu '{text}' không hợp lệ. Dùng mã #RRGGBB hoặc một tone: {known}")


def diagram_direction(spec: dict, default: str = "LR") -> str:
    value = as_text(spec.get("direction") or default).upper()
    if value not in {"LR", "RL", "TB", "BT"}:
        raise SpecError("direction của diagram phải là LR, RL, TB hoặc BT")
    return value


def edge_parts(edge: dict) -> dict:
    edge = as_dict(edge, "cạnh")
    source = as_text(edge.get("from", edge.get("source")))
    target = as_text(edge.get("to", edge.get("target")))
    if not source or not target:
        raise SpecError("Mỗi cạnh cần from và to")
    style = as_text(edge.get("style") or "solid").lower()
    if style not in {"solid", "dashed", "dotted", "bold"}:
        raise SpecError("style của cạnh phải là solid, dashed, dotted hoặc bold")
    painted = edge.get("color") not in (None, "") or edge.get("tone") not in (None, "")
    color = resolve_color(edge.get("color") or edge.get("tone"), THEME["edge"])
    if style == "bold" and not painted:
        color = THEME["primary"]
    direction = as_text(edge.get("direction") or edge.get("dir") or "forward").lower()
    if direction not in {"forward", "back", "both"}:
        raise SpecError("direction của cạnh phải là forward, back hoặc both")
    constraint = edge.get("constraint")
    loose = constraint is False or as_text(constraint).lower() == "false"
    return {
        "source": source,
        "target": target,
        "label": as_text(edge.get("label")),
        "color": color,
        "style": style,
        "penwidth": "2.2" if style == "bold" else "1.35",
        "direction": direction,
        "constraint": loose,
    }


def parse_mark(value, bound: str = "start") -> date:
    raw = as_text(value)
    matched = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if matched:
        year, month = int(matched.group(1)), int(matched.group(2))
        _check_month(year, month, raw)
        return date(year, month, 1)
    matched = re.fullmatch(r"(\d{4})-(\d{2})", raw)
    if matched:
        year, month = int(matched.group(1)), int(matched.group(2))
        _check_month(year, month, raw)
        return date(year, month, 1)
    matched = re.fullmatch(r"(\d{4})-Q([1-4])", raw, flags=re.IGNORECASE)
    if matched:
        year = int(matched.group(1))
        quarter = int(matched.group(2))
        if bound == "end":
            month = quarter * 3
        elif bound == "point":
            month = quarter * 3 - 1
        else:
            month = (quarter - 1) * 3 + 1
        return date(year, month, 1)
    raise SpecError(f"Mốc '{raw}' không hợp lệ. Dùng YYYY-MM hoặc YYYY-Qn")


def months_between(start: date, end: date) -> list[date]:
    if (end.year, end.month) < (start.year, start.month):
        raise SpecError("Mốc kết thúc đang đứng trước mốc bắt đầu")
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(date(year, month, 1))
        month += 1
        if month == 13:
            month = 1
            year += 1
        if len(months) > 48:
            raise SpecError("Khoảng thời gian tối đa là 48 tháng")
    return months


def month_index(months: list[date], mark: date, label: str) -> int:
    for index, month in enumerate(months):
        if month.year == mark.year and month.month == mark.month:
            return index
    raise SpecError(f"{label} nằm ngoài khoảng thời gian của roadmap")


def load_spec(text: str) -> dict:
    text = text.lstrip("\ufeff").strip()
    if not text:
        raise SpecError("Spec đang trống")
    if len(text) > 100_000:
        raise SpecError("Spec dài hơn 100KB")
    try:
        if text.startswith("{"):
            data = json.loads(text)
        else:
            data = yaml.safe_load(text)
    except Exception as exc:
        raise SpecError(f"Không đọc được spec: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError("Spec phải là một object YAML hoặc JSON")
    return data


def _check_month(year: int, month: int, raw: str) -> None:
    if month < 1 or month > 12:
        raise SpecError(f"Tháng trong '{raw}' không hợp lệ")
    if year < 1990 or year > 2200:
        raise SpecError(f"Năm trong '{raw}' không hợp lệ")
