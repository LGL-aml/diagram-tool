from app.runtime import GRAPHVIZ_HELP, ensure_graphviz_on_path
from app.spec import SpecError, as_dict, as_list, as_text, diagram_direction, edge_parts, require_id
from app.svgutil import wrap_words
from app.theme import CLUSTER_FILLS, THEME

_SHAPES = {
    "box": "box",
    "process": "box",
    "ellipse": "ellipse",
    "start": "ellipse",
    "end": "ellipse",
    "terminator": "ellipse",
    "diamond": "diamond",
    "decision": "diamond",
    "circle": "circle",
    "cylinder": "cylinder",
    "database": "cylinder",
    "hexagon": "hexagon",
    "parallelogram": "parallelogram",
    "input": "parallelogram",
    "note": "note",
    "folder": "folder",
    "component": "component",
}

_KINDS = {
    "person": {
        "shape": "box",
        "style": "rounded,filled",
        "fillcolor": THEME["primary_soft"],
        "color": THEME["primary"],
        "fontcolor": THEME["ink"],
    },
    "system": {
        "shape": "box",
        "style": "rounded,filled",
        "fillcolor": THEME["primary"],
        "color": THEME["primary_deep"],
        "fontcolor": "#FFFFFF",
        "penwidth": "1.8",
        "fontsize": "14",
    },
    "external": {
        "shape": "box",
        "style": "rounded,dashed,filled",
        "fillcolor": THEME["paper"],
        "color": THEME["accent"],
        "fontcolor": THEME["ink"],
    },
    "datastore": {
        "shape": "cylinder",
        "style": "filled",
        "fillcolor": THEME["paper"],
        "color": THEME["primary"],
        "fontcolor": THEME["ink"],
    },
    "database": {
        "shape": "cylinder",
        "style": "filled",
        "fillcolor": THEME["paper"],
        "color": THEME["primary"],
        "fontcolor": THEME["ink"],
    },
}


def render_graph(spec: dict) -> tuple[str, list[str]]:
    if ensure_graphviz_on_path() is None:
        raise SpecError(GRAPHVIZ_HELP)

    kind = as_text(spec.get("type")).lower()
    default_direction = "TB" if kind == "flow" else "LR"
    direction = diagram_direction(spec, default_direction)
    splines = as_text(spec.get("splines") or "spline").lower()
    if splines not in {"spline", "ortho", "polyline", "curved", "line"}:
        raise SpecError("splines phải là spline, ortho, polyline, curved hoặc line")

    nodes = as_list(spec.get("nodes"), "nodes")
    clusters = as_list(spec.get("clusters"), "clusters")
    edges = [edge_parts(edge) for edge in as_list(spec.get("edges"), "edges")]
    if not nodes and not clusters:
        raise SpecError("Diagram cần nodes hoặc clusters")

    import graphviz

    graph = graphviz.Digraph("G", format="svg", encoding="utf-8")
    graph.attr(
        rankdir=direction,
        bgcolor="transparent",
        splines=splines,
        pad="0.45",
        nodesep="0.5",
        ranksep="0.72",
        fontname=THEME["font"],
        fontsize="13",
        fontcolor=THEME["ink"],
        charset="UTF-8",
        forcelabels="true",
    )
    graph.attr("node", fontname=THEME["font"], fontsize="12", fontcolor=THEME["ink"])
    graph.attr(
        "edge",
        fontname=THEME["font"],
        fontsize="10",
        fontcolor=THEME["muted"],
        color=THEME["edge"],
        penwidth="1.35",
        arrowsize="0.75",
    )

    created: set[str] = set()
    counter = {"n": 0}

    def add_nodes(target, items):
        for raw in items or []:
            node = as_dict(raw, "node")
            node_id = require_id(node.get("id"), "id của node")
            if node_id in created:
                raise SpecError(f"Trùng id '{node_id}'")
            label = as_text(node.get("label"))
            if not label:
                raise SpecError(f"Node '{node_id}' cần label")
            attrs = _node_attrs(node)
            target.node(node_id, _graph_label(label, attrs["shape"]), **attrs)
            created.add(node_id)
            if len(created) > 80:
                raise SpecError("Một diagram giữ tối đa 80 node")

    def add_clusters(target, items, depth: int):
        if depth > 4:
            raise SpecError("Cluster lồng nhau tối đa 4 cấp")
        for raw in items or []:
            cluster = as_dict(raw, "cluster")
            name = as_text(cluster.get("name"))
            if not name:
                raise SpecError("Cluster cần name")
            index = counter["n"]
            counter["n"] += 1
            with target.subgraph(name=f"cluster_{index}") as sub:
                sub.attr(label=name, **_cluster_attr(index))
                add_nodes(sub, cluster.get("nodes"))
                add_clusters(sub, cluster.get("clusters"), depth + 1)

    add_nodes(graph, nodes)
    add_clusters(graph, clusters, 1)
    if len(edges) > 160:
        raise SpecError("Một diagram giữ tối đa 160 cạnh")
    for edge in edges:
        if edge["source"] not in created or edge["target"] not in created:
            raise SpecError(f"Cạnh tham chiếu node không tồn tại: {edge['source']} → {edge['target']}")
        attrs = {
            "color": edge["color"],
            "penwidth": edge["penwidth"],
            "fontname": THEME["font"],
            "fontsize": "10",
            "fontcolor": THEME["muted"],
        }
        if edge["label"]:
            attrs["label"] = edge["label"]
        if edge["style"] in {"dashed", "dotted"}:
            attrs["style"] = edge["style"]
        if edge["direction"] == "both":
            attrs["dir"] = "both"
        elif edge["direction"] == "back":
            attrs["dir"] = "back"
        if edge["constraint"]:
            attrs["constraint"] = "false"
        graph.edge(edge["source"], edge["target"], **attrs)

    try:
        svg = graph.pipe(format="svg", encoding="utf-8")
    except Exception as exc:
        raise _graphviz_error(exc) from exc
    if isinstance(svg, bytes):
        svg = svg.decode("utf-8")
    return svg, []


def _node_attrs(node: dict) -> dict:
    kind = as_text(node.get("kind")).lower()
    if kind:
        if kind not in _KINDS:
            raise SpecError("kind phải là person, system, external hoặc datastore")
        attrs = {
            "fontname": THEME["font"],
            "fontsize": "12",
            "penwidth": "1.4",
            "margin": "0.16,0.1",
        }
        attrs.update(_KINDS[kind])
        return attrs

    shape_name = as_text(node.get("shape") or "box").lower()
    if shape_name not in _SHAPES:
        raise SpecError(f"shape '{shape_name}' không được hỗ trợ")
    shape = _SHAPES[shape_name]
    fill = THEME["paper"]
    stroke = THEME["primary"]
    style = "filled"
    if shape in {"box", "component", "note", "folder"}:
        style = "rounded,filled"
    if shape == "diamond":
        fill = THEME["accent_soft"]
        stroke = THEME["accent"]
    elif shape in {"ellipse", "hexagon", "parallelogram"}:
        fill = THEME["primary_soft"]
    return {
        "shape": shape,
        "style": style,
        "fillcolor": fill,
        "color": stroke,
        "fontname": THEME["font"],
        "fontsize": "12",
        "fontcolor": THEME["ink"],
        "penwidth": "1.4",
        "margin": "0.16,0.1",
    }


def _graph_label(text: str, shape: str) -> str:
    if "\n" in text:
        return text
    limit = 16 if shape == "diamond" else 26
    if len(text) <= limit:
        return text
    return "\n".join(wrap_words(text, limit))


def _cluster_attr(index: int) -> dict:
    fill = CLUSTER_FILLS[index % len(CLUSTER_FILLS)]
    return {
        "style": "rounded,filled",
        "fillcolor": fill,
        "color": THEME["primary"],
        "fontname": THEME["font"],
        "fontsize": "13",
        "fontcolor": THEME["primary"],
        "penwidth": "1.3",
        "labeljust": "l",
        "margin": "14",
    }


def _graphviz_error(exc: Exception) -> SpecError:
    if exc.__class__.__name__ == "ExecutableNotFound" or "failed to execute" in str(exc).lower():
        return SpecError(GRAPHVIZ_HELP)
    stderr = getattr(exc, "stderr", "") or ""
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", "replace")
    detail = (stderr or str(exc)).strip()
    last = detail.splitlines()[-1] if detail else exc.__class__.__name__
    return SpecError(f"Graphviz không kết xuất được hình: {last}")
