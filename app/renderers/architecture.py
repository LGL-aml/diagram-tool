import importlib
import re
import shutil
import uuid
from pathlib import Path

from app.paths import RENDER_DIR
from app.runtime import GRAPHVIZ_HELP, ensure_graphviz_on_path
from app.spec import SpecError, as_dict, as_list, as_text, edge_parts, require_id
from app.svgutil import embed_images
from app.theme import CLUSTER_FILLS, THEME

_ICON = re.compile(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+")
_ROOTS = {
    "alibabacloud",
    "aws",
    "azure",
    "c4",
    "custom",
    "digitalocean",
    "elastic",
    "firebase",
    "gcp",
    "generic",
    "gis",
    "ibm",
    "k8s",
    "oci",
    "onprem",
    "openstack",
    "outscale",
    "programming",
    "saas",
}


def render_architecture(spec: dict) -> tuple[str, list[str]]:
    if ensure_graphviz_on_path() is None:
        raise SpecError(GRAPHVIZ_HELP)

    nodes = as_list(spec.get("nodes"), "nodes")
    clusters = as_list(spec.get("clusters"), "clusters")
    edges = as_list(spec.get("edges"), "edges")
    if not nodes and not clusters:
        raise SpecError("Architecture cần nodes hoặc clusters")

    ids: set[str] = set()
    _validate_nodes(nodes, ids)
    _validate_clusters(clusters, ids, depth=1)
    if len(ids) > 80:
        raise SpecError("Một architecture diagram giữ tối đa 80 node")
    if len(edges) > 160:
        raise SpecError("Một architecture diagram giữ tối đa 160 cạnh")
    prepared = [edge_parts(edge) for edge in edges]
    missing = [f"{item['source']} → {item['target']}" for item in prepared if item["source"] not in ids or item["target"] not in ids]
    if missing:
        raise SpecError("Cạnh tham chiếu node không tồn tại: " + ", ".join(missing))

    curve = "ortho" if as_text(spec.get("splines") or "curved").lower() == "ortho" else "curved"
    from app.spec import diagram_direction

    direction = diagram_direction(spec, "LR")
    tmp = RENDER_DIR / f"arch-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=True)
    base = tmp / "diagram"
    held: Exception | None = None
    try:
        from diagrams import Cluster, Diagram, Edge, setdiagram

        try:
            with Diagram(
                "",
                filename=str(base),
                show=False,
                direction=direction,
                curvestyle=curve,
                outformat="svg",
                graph_attr={
                    "charset": "UTF-8",
                    "bgcolor": "transparent",
                    "pad": "0.4",
                    "nodesep": "0.7",
                    "ranksep": "0.9",
                    "fontname": THEME["font"],
                    "fontsize": "14",
                    "fontcolor": THEME["ink"],
                    "label": "",
                    "forcelabels": "true",
                },
                node_attr={
                    "fontname": THEME["font"],
                    "fontsize": "12",
                    "fontcolor": THEME["ink"],
                },
                edge_attr={
                    "fontname": THEME["font"],
                    "fontsize": "11",
                    "fontcolor": THEME["muted"],
                    "color": THEME["edge"],
                    "penwidth": "1.35",
                    "arrowsize": "0.75",
                },
            ):
                created: dict = {}
                counter = {"n": 0}

                def add_nodes(items):
                    for node in items or []:
                        created[node["id"]] = load_icon(node["icon"])(str(node["label"]))

                def add_clusters(items):
                    for cluster in items or []:
                        index = counter["n"]
                        counter["n"] += 1
                        with Cluster(str(cluster["name"]), graph_attr=_cluster_attr(index)):
                            add_nodes(cluster.get("nodes"))
                            add_clusters(cluster.get("clusters"))

                add_nodes(nodes)
                add_clusters(clusters)
                for item in prepared:
                    link = Edge(
                        label=item["label"],
                        color=item["color"],
                        style="" if item["style"] in {"solid", "bold"} else item["style"],
                        fontname=THEME["font"],
                        fontsize="11",
                        fontcolor=THEME["muted"],
                        penwidth=item["penwidth"],
                        **({"constraint": "false"} if item["constraint"] else {}),
                    )
                    link.node = created[item["source"]]
                    if item["direction"] == "back":
                        link.reverse = True
                    elif item["direction"] == "both":
                        link.forward = True
                        link.reverse = True
                    else:
                        link.forward = True
                    link.connect(created[item["target"]])
        except SpecError:
            raise
        except Exception as exc:
            held = exc
        finally:
            setdiagram(None)

        svg_file = _find_svg(tmp)
        if svg_file is None:
            if held:
                raise _graphviz_error(held) from held
            raise SpecError("diagrams không tạo được SVG")
        svg, warnings = embed_images(svg_file.read_text(encoding="utf-8"), [tmp])
        if held and not isinstance(held, FileNotFoundError):
            warnings.append(str(held).splitlines()[-1][:240])
        return svg, warnings
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_icon(path: str):
    raw = as_text(path)
    if raw.startswith("diagrams."):
        raw = raw[len("diagrams.") :]
    if not _ICON.fullmatch(raw):
        raise SpecError(f"Icon không hợp lệ: {path}")
    root = raw.split(".", 1)[0]
    if root not in _ROOTS:
        raise SpecError(f"Nhóm icon '{root}' không có trong diagrams")
    module_name, class_name = raw.rsplit(".", 1)
    try:
        module = importlib.import_module(f"diagrams.{module_name}")
        icon = getattr(module, class_name)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise SpecError(f"Không tìm thấy icon '{raw}'. Hãy tìm trong danh mục icon.") from exc
    return icon


def _validate_nodes(nodes, ids: set[str]) -> None:
    for node in nodes:
        node = as_dict(node, "node")
        node_id = require_id(node.get("id"), "id của node")
        if node_id in ids:
            raise SpecError(f"Trùng id '{node_id}'")
        if not as_text(node.get("label")):
            raise SpecError(f"Node '{node_id}' cần label")
        if not as_text(node.get("icon")):
            raise SpecError(f"Node '{node_id}' cần icon, ví dụ onprem.database.PostgreSQL")
        load_icon(node["icon"])
        ids.add(node_id)


def _validate_clusters(clusters, ids: set[str], depth: int) -> None:
    if depth > 4:
        raise SpecError("Cluster lồng nhau tối đa 4 cấp")
    for cluster in clusters:
        cluster = as_dict(cluster, "cluster")
        if not as_text(cluster.get("name")):
            raise SpecError("Cluster cần name")
        _validate_nodes(as_list(cluster.get("nodes"), "nodes"), ids)
        _validate_clusters(as_list(cluster.get("clusters"), "clusters"), ids, depth + 1)


def _cluster_attr(index: int) -> dict:
    fill = CLUSTER_FILLS[index % len(CLUSTER_FILLS)]
    return {
        "style": "rounded,filled",
        "fillcolor": fill,
        "bgcolor": fill,
        "pencolor": THEME["primary"],
        "color": THEME["primary"],
        "fontname": THEME["font"],
        "fontsize": "13",
        "fontcolor": THEME["primary"],
        "penwidth": "1.3",
        "labeljust": "l",
        "margin": "16",
    }


def _find_svg(folder: Path) -> Path | None:
    files = list(folder.glob("*.svg"))
    if not files:
        return None
    for path in files:
        if path.stem == "diagram":
            return path
    return files[0]


def _graphviz_error(exc: Exception) -> SpecError:
    if exc.__class__.__name__ == "ExecutableNotFound" or "failed to execute" in str(exc).lower():
        return SpecError(GRAPHVIZ_HELP)
    stderr = getattr(exc, "stderr", "") or ""
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", "replace")
    detail = (stderr or str(exc)).strip()
    last = detail.splitlines()[-1] if detail else exc.__class__.__name__
    return SpecError(f"Graphviz không kết xuất được hình: {last}")
