import inspect
import re
import shutil
import uuid

from app.paths import RENDER_DIR
from app.spec import SpecError, as_dict, as_list, as_text
from app.theme import THEME

_LIBRARIES = {
    "electrical": "schemdraw.elements",
    "flow": "schemdraw.flow",
    "dsp": "schemdraw.dsp",
    "logic": "schemdraw.logic",
}
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ELEMENT = re.compile(r"[A-Z][A-Za-z0-9_]*")


def render_schematic(spec: dict) -> tuple[str, list[str]]:
    library_name = as_text(spec.get("library") or "electrical").lower()
    if library_name not in _LIBRARIES:
        raise SpecError("library phải là electrical, flow, dsp hoặc logic")
    elements = as_list(spec.get("elements"), "elements")
    if not elements:
        raise SpecError("Schematic cần elements")
    if len(elements) > 40:
        raise SpecError("Schematic giữ tối đa 40 phần tử")

    import importlib

    import schemdraw
    from schemdraw import elements as electrical

    module = importlib.import_module(_LIBRARIES[library_name])
    drawing = schemdraw.Drawing(show=False, canvas="svg")
    drawing.config(
        fontsize=12,
        font=THEME["font"],
        color=THEME["primary"],
        lw=1.6,
        margin=0.45,
        inches_per_unit=1.35,
    )
    default_loc = "center" if library_name == "flow" else "top"

    for index, raw in enumerate(elements, start=1):
        item = as_dict(raw, "phần tử")
        element_name = as_text(item.get("element"))
        if not _ELEMENT.fullmatch(element_name):
            raise SpecError(f"Phần tử thứ {index} cần tên class, ví dụ Resistor hoặc Filter")
        cls = _resolve(module, electrical, element_name)
        try:
            element = cls(**_options(item.get("options")))
        except TypeError as exc:
            raise SpecError(f"{element_name} không nhận options đã khai báo: {exc}") from exc
        direction = as_text(item.get("direction") or "right").lower()
        if direction not in {"right", "left", "up", "down"}:
            raise SpecError("direction của phần tử phải là right, left, up hoặc down")
        element = getattr(element, direction)()
        if item.get("length") not in (None, ""):
            if not hasattr(element, "length"):
                raise SpecError(f"{element_name} không có length")
            try:
                element = element.length(float(item["length"]))
            except (TypeError, ValueError) as exc:
                raise SpecError(f"length của {element_name} phải là số") from exc
        label = as_text(item.get("label"))
        if label:
            loc = as_text(item.get("label_loc") or default_loc).lower()
            if loc not in {"top", "bottom", "left", "right", "center"}:
                raise SpecError("label_loc phải là top, bottom, left, right hoặc center")
            element = element.label(label, loc=loc, color=THEME["ink"], font=THEME["font"])
        drawing += element

    tmp = RENDER_DIR / f"sch-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "schematic.svg"
    try:
        drawing.save(str(path), transparent=True)
        return path.read_text(encoding="utf-8"), []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _resolve(module, electrical, name: str):
    for source in (module, electrical):
        candidate = getattr(source, name, None)
        if inspect.isclass(candidate):
            return candidate
    raise SpecError(f"Không có phần tử {name} trong thư viện đã chọn")


def _options(raw) -> dict:
    if raw in (None, ""):
        return {}
    raw = as_dict(raw, "options")
    options = {}
    for key, value in raw.items():
        if not _NAME.fullmatch(str(key)):
            raise SpecError(f"option không hợp lệ: {key}")
        if isinstance(value, (str, int, float)) or value is None or isinstance(value, bool):
            options[str(key)] = value
        else:
            raise SpecError(f"option {key} chỉ nhận chuỗi, số hoặc boolean")
    return options
