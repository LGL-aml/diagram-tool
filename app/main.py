import io
import logging
import zipfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import __version__
from app.engine import render_text
from app.library import delete_doc, list_docs, read_doc, save_doc, skeleton
from app.paths import STATIC, TEMPLATES
from app.runtime import ensure_graphviz_on_path
from app.spec import SpecError
from app.theme import RENDERERS, THEME

logger = logging.getLogger("diagram_studio")


class SpecIn(BaseModel):
    spec: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_graphviz_on_path()
    yield


app = FastAPI(title="Diagram Studio", version=__version__, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/api/health")
def health():
    dot = ensure_graphviz_on_path()
    return {
        "ok": True,
        "version": __version__,
        "theme": THEME["name"],
        "graphviz": dot,
        "types": RENDERERS,
    }


@app.get("/api/docs")
def docs():
    return {"docs": list_docs()}


@app.get("/api/docs/{kind}/{name}")
def doc(kind: str, name: str):
    try:
        return read_doc(kind, name)
    except SpecError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/skeletons/{kind}")
def skeleton_route(kind: str):
    try:
        return {"type": kind, "renderer": RENDERERS.get(kind, ""), "spec": skeleton(kind)}
    except SpecError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/catalog")
def catalog():
    from app.catalog import load_catalog

    return load_catalog()


@app.post("/api/render")
def render(body: SpecIn):
    _limit(body.spec)
    try:
        figure = render_text(body.spec)
    except SpecError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "svg": figure.svg,
        "renderer": figure.renderer,
        "warnings": figure.warnings,
        "type": figure.diagram_type,
        "title": figure.title,
        "filename": figure.filename,
    }


@app.post("/api/specs/{name}")
def save(name: str, body: SpecIn):
    _limit(body.spec)
    try:
        return save_doc(name, body.spec)
    except SpecError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/api/specs/{name}")
def delete(name: str):
    try:
        delete_doc(name)
    except SpecError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True}


@app.post("/api/pack.zip")
def pack():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(TEMPLATES.glob("*.yaml")):
            text = path.read_text(encoding="utf-8")
            try:
                figure = render_text(text)
            except SpecError as exc:
                raise HTTPException(400, f"{path.name}: {exc}") from exc
            archive.writestr(f"{path.stem}.yaml", text)
            archive.writestr(f"{path.stem}.svg", figure.svg)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=technology-diagrams.zip"},
    )


def _limit(text: str) -> None:
    if len(text) > 100_000:
        raise HTTPException(400, "Spec dài hơn 100KB")
