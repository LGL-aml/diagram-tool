import ast
import json
from pathlib import Path

from app.paths import RENDER_DIR

_PRETTY = {
    "aws": "AWS",
    "gcp": "GCP",
    "oci": "OCI",
    "ibm": "IBM",
    "k8s": "Kubernetes",
    "onprem": "On-prem",
    "saas": "SaaS",
    "alibabacloud": "Alibaba Cloud",
    "digitalocean": "DigitalOcean",
    "openstack": "OpenStack",
    "outscale": "Outscale",
    "firebase": "Firebase",
    "elastic": "Elastic",
    "gis": "GIS",
    "c4": "C4",
    "programming": "Programming",
    "generic": "Generic",
    "azure": "Azure",
    "custom": "Custom",
}


def load_catalog() -> dict:
    import diagrams

    version = getattr(diagrams, "__version__", "0")
    cache = RENDER_DIR / "catalog.json"
    if cache.is_file():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached and cached.get("version") == version:
            return {"groups": cached["groups"], "count": cached["count"]}

    groups = _build_groups(Path(diagrams.__file__).resolve().parent)
    count = sum(len(group["icons"]) for group in groups)
    cache.write_text(
        json.dumps({"version": version, "count": count, "groups": groups}, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"groups": groups, "count": count}


def _build_groups(root: Path) -> list[dict]:
    records: list[tuple[str, str, list[str], bool]] = []
    for path in root.rglob("*.py"):
        relative = path.relative_to(root).with_suffix("")
        parts = list(relative.parts)
        if any(part.startswith("_") and part != "__init__" for part in parts):
            continue
        if parts[-1] == "__init__":
            parts = parts[:-1]
        module = ".".join(parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [name for base in node.bases if (name := _base_name(base))]
            public = bool(module) and not node.name.startswith("_")
            qual = f"{module}.{node.name}" if module else node.name
            records.append((qual, node.name, bases, public))

    known = {"Node"}
    done: set[str] = set()
    selected: list[str] = []
    changed = True
    while changed:
        changed = False
        for qual, simple, bases, public in records:
            if qual in done:
                continue
            if any(base in known for base in bases):
                done.add(qual)
                known.add(simple)
                changed = True
                if public:
                    selected.append(qual)

    grouped: dict[str, list[str]] = {}
    for qual in selected:
        module, _, _name = qual.rpartition(".")
        grouped.setdefault(module, []).append(qual)

    groups = []
    for module in sorted(grouped):
        groups.append(
            {
                "id": module,
                "label": _pretty(module),
                "icons": sorted(grouped[module]),
            }
        )
    return groups


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _pretty(module: str) -> str:
    parts = module.split(".")
    head = _PRETTY.get(parts[0], parts[0].replace("_", " ").title())
    tail = " · ".join(part.replace("_", " ").title() for part in parts[1:])
    return f"{head} · {tail}" if tail else head
