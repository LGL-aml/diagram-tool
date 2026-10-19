THEME = {
    "name": "report",
    "font": "Segoe UI",
    "font_family": "Segoe UI, Arial, sans-serif",
    "ink": "#10233F",
    "muted": "#5C6B7A",
    "faint": "#8AA0B4",
    "line": "#D5E0EA",
    "primary": "#1B4F8A",
    "primary_deep": "#0C2340",
    "primary_soft": "#E7F0F8",
    "paper": "#FFFFFF",
    "lane": "#F7FAFC",
    "accent": "#C56A12",
    "accent_soft": "#FBF3E8",
    "done": "#0E7A45",
    "done_soft": "#E6F5EE",
    "risk": "#B42318",
    "risk_soft": "#FDECEC",
    "edge": "#5E7388",
    "footer": "Technology report",
}

CLUSTER_FILLS = ("#E7F0F8", "#F4F7FB", "#FBF3E8", "#E6F5EE")

TYPE_LABELS = {
    "architecture": "ARCHITECTURE",
    "context": "CONTEXT",
    "flow": "FLOW",
    "dependency": "DEPENDENCY",
    "sequence": "SEQUENCE",
    "stack": "STACK",
    "roadmap": "ROADMAP",
    "schematic": "SCHEMATIC",
}

RENDERERS = {
    "architecture": "diagrams · Graphviz",
    "context": "Graphviz",
    "flow": "Graphviz",
    "dependency": "Graphviz",
    "sequence": "SVG · theme chung",
    "stack": "SVG · theme chung",
    "roadmap": "SVG · theme chung",
    "schematic": "Schemdraw",
}

TONES = {
    "primary": THEME["primary"],
    "ink": THEME["ink"],
    "muted": THEME["muted"],
    "accent": THEME["accent"],
    "done": THEME["done"],
    "risk": THEME["risk"],
    "edge": THEME["edge"],
}

FRAME_WIDTH = 1200
CONTENT_WIDTH = 1120
