import yaml

from app.paths import SPECS, TEMPLATES
from app.spec import SpecError, as_text, load_spec, safe_name
from app.theme import RENDERERS

SKELETONS = {
    "context": """type: context
title: Bối cảnh hệ thống
subtitle: C4 · mức context
footer: Technology report
direction: LR
nodes:
  - id: user
    label: Người dùng
    kind: person
  - id: system
    label: Hệ thống nội bộ
    kind: system
  - id: external
    label: Hệ thống ngoài
    kind: external
edges:
  - from: user
    to: system
    label: Sử dụng
  - from: system
    to: external
    label: Tích hợp
""",
    "architecture": """type: architecture
title: Kiến trúc hệ thống
footer: Technology report
direction: LR
nodes:
  - id: user
    label: Người dùng
    icon: onprem.client.Users
clusters:
  - name: Ứng dụng
    nodes:
      - id: api
        label: API
        icon: aws.network.APIGateway
      - id: service
        label: Service
        icon: k8s.compute.Pod
  - name: Dữ liệu
    nodes:
      - id: db
        label: PostgreSQL
        icon: onprem.database.PostgreSQL
edges:
  - from: user
    to: api
    label: HTTPS
  - from: api
    to: service
  - from: service
    to: db
""",
    "flow": """type: flow
title: Quy trình
footer: Technology report
direction: TB
nodes:
  - id: start
    label: Bắt đầu
    shape: ellipse
  - id: review
    label: Kiểm tra
    shape: diamond
  - id: build
    label: Thực hiện
    shape: box
  - id: done
    label: Hoàn tất
    shape: ellipse
edges:
  - from: start
    to: review
  - from: review
    to: build
    label: Đạt
    tone: done
  - from: review
    to: start
    label: Làm lại
    style: dashed
    tone: accent
    constraint: false
  - from: build
    to: done
""",
    "dependency": """type: dependency
title: Phụ thuộc dịch vụ
footer: Technology report
direction: LR
nodes:
  - id: web
    label: Web
    shape: box
  - id: api
    label: API
    shape: box
  - id: db
    label: Database
    shape: cylinder
edges:
  - from: web
    to: api
  - from: api
    to: db
""",
    "sequence": """type: sequence
title: Luồng gọi
footer: Technology report
actors:
  - id: client
    label: Client
    kind: person
  - id: api
    label: API
  - id: db
    label: Database
messages:
  - from: client
    to: api
    label: Request
  - from: api
    to: db
    label: Query
  - from: db
    to: api
    label: Rows
    style: return
  - from: api
    to: client
    label: Response
    style: return
""",
    "stack": """type: stack
title: Technology stack
footer: Technology report
layers:
  - name: Trải nghiệm
    items: [Web, Mobile]
  - name: Giao tiếp
    items: [API Gateway, BFF]
  - name: Nghiệp vụ
    items: [Order, Payment, Identity]
  - name: Dữ liệu
    items: [PostgreSQL, Redis, Kafka]
  - name: Vận hành
    items: [Kubernetes, Observability, CI/CD]
""",
    "roadmap": """type: roadmap
title: Lộ trình công nghệ
footer: Technology report
start: 2026-01
end: 2026-12
today: 2026-10
lanes:
  - name: Nền tảng
    items:
      - label: Nền tảng chạy thật
        start: 2026-01
        end: 2026-04
        status: done
      - label: Mở rộng năng lực
        start: 2026-05
        end: 2026-09
        status: active
      - label: Vùng dự phòng
        start: 2026-10
        end: 2026-12
        status: planned
milestones:
  - label: Cắt hạ tầng cũ
    at: 2026-06
""",
    "schematic": """type: schematic
title: Chuỗi xử lý tín hiệu
subtitle: Schemdraw · dsp
footer: Technology report
library: dsp
elements:
  - element: Filter
    direction: right
    label: BPF
    options:
      response: bp
  - element: Line
    direction: right
    length: 0.4
  - element: Amp
    direction: right
    label: LNA
  - element: Line
    direction: right
    length: 0.4
  - element: Mixer
    direction: right
    label: Mixer
  - element: Line
    direction: right
    length: 0.4
  - element: Adc
    direction: right
    label: ADC
""",
}


def list_docs() -> list[dict]:
    docs = [_meta(path, "builtin") for path in sorted(TEMPLATES.glob("*.yaml"))]
    docs.extend(_meta(path, "user") for path in sorted(SPECS.glob("*.yaml")))
    return docs


def read_doc(kind: str, name: str) -> dict:
    path = _path(kind, name)
    info = _meta(path, kind)
    info["spec"] = path.read_text(encoding="utf-8")
    return info


def save_doc(name: str, text: str) -> dict:
    safe = safe_name(name)
    spec = load_spec(text)
    if as_text(spec.get("type")).lower() not in RENDERERS or not as_text(spec.get("title")):
        raise SpecError("Spec cần type hợp lệ và title trước khi lưu")
    path = SPECS / f"{safe}.yaml"
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return read_doc("user", safe)


def delete_doc(name: str) -> None:
    path = SPECS / f"{safe_name(name)}.yaml"
    if not path.is_file():
        raise SpecError("Không tìm thấy spec")
    path.unlink()


def skeleton(kind: str) -> str:
    if kind not in SKELETONS:
        raise SpecError("Chưa có khung cho loại diagram này")
    return SKELETONS[kind]


def _path(kind: str, name: str):
    safe = safe_name(name)
    root = TEMPLATES if kind == "builtin" else SPECS if kind == "user" else None
    if root is None:
        raise SpecError("Không tìm thấy spec")
    path = root / f"{safe}.yaml"
    if not path.is_file():
        raise SpecError("Không tìm thấy spec")
    return path


def _meta(path, kind: str) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        error = ""
        if not isinstance(data, dict):
            data = {}
            error = "Spec không phải object"
    except Exception as exc:
        data = {}
        error = str(exc)
    diagram_type = as_text(data.get("type")).lower()
    return {
        "id": f"{kind}/{path.stem}",
        "kind": kind,
        "name": path.stem,
        "title": as_text(data.get("title")) or path.stem,
        "type": diagram_type,
        "renderer": RENDERERS.get(diagram_type, ""),
        "builtin": kind == "builtin",
        "error": error,
    }
