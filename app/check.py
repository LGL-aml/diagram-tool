from app.engine import render_text
from app.library import list_docs, read_doc
from app.paths import OUTPUT_DIR
from app.runtime import ensure_graphviz_on_path
from app.spec import SpecError


def main() -> None:
    dot = ensure_graphviz_on_path()
    print(f"graphviz: {dot or 'MISSING'}")
    OUTPUT_DIR.mkdir(exist_ok=True)
    failed = False
    for doc in list_docs():
        if not doc["builtin"]:
            continue
        loaded = read_doc(doc["kind"], doc["name"])
        try:
            figure = render_text(loaded["spec"])
        except SpecError as exc:
            failed = True
            print(f"FAIL  {doc['name']}: {exc}")
            continue
        target = OUTPUT_DIR / f"{doc['name']}.svg"
        target.write_text(figure.svg, encoding="utf-8")
        width_ok = 'width="1200"' in figure.svg
        title_ok = figure.title in figure.svg
        print(
            f"OK    {doc['name']:18} {figure.diagram_type:14} "
            f"{target.stat().st_size:8} bytes  width={width_ok} title={title_ok} "
            f"warnings={len(figure.warnings)}"
        )
        for warning in figure.warnings:
            print(f"      ! {warning}")
        if not width_ok or not title_ok:
            failed = True
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
