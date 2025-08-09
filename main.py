from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, sqlite3, uuid, datetime, pathlib

APP_ENV = os.getenv("APP_ENV", "dev")
DATA_DIR = pathlib.Path("./data/uploads").resolve()
app = FastAPI(title="BlobDrop", version="0.1.0")

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = pathlib.Path("./data/blobdrop.db"); DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(pathlib.Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

def db():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn
with db() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS drops (id TEXT PRIMARY KEY, note TEXT, ttl_hours INTEGER, created_at TEXT, uploads INTEGER DEFAULT 0)""")
    c.commit()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create")
def create_drop(ttl_hours: int = Form(48), note: str = Form("")):
    drop_id = uuid.uuid4().hex[:10]
    with db() as c:
        c.execute("INSERT INTO drops (id,note,ttl_hours,created_at) VALUES (?,?,?,?)",
                  (drop_id, note.strip(), int(ttl_hours), datetime.datetime.utcnow().isoformat()))
        c.commit()
    return RedirectResponse(url=f"/created/{drop_id}", status_code=303)

@app.get("/created/{drop_id}", response_class=HTMLResponse)
def created(request: Request, drop_id: str):
    return templates.TemplateResponse("created.html", {"request": request, "drop_id": drop_id})

@app.get("/d/{drop_id}", response_class=HTMLResponse)
def drop_page(request: Request, drop_id: str):
    with db() as c:
        row = c.execute("SELECT * FROM drops WHERE id=?", (drop_id,)).fetchone()
    if not row:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Invalid link."}, status_code=404)
    return templates.TemplateResponse("drop.html", {"request": request, "drop_id": drop_id, "note": row["note"]})

@app.post("/d/{drop_id}/upload")
async def upload_file(drop_id: str, file: UploadFile = File(...)):
    with db() as c:
        row = c.execute("SELECT 1 FROM drops WHERE id=?", (drop_id,)).fetchone()
    if not row: raise HTTPException(404, "Invalid link")
    dest = DATA_DIR / drop_id; dest.mkdir(parents=True, exist_ok=True)
    with open(dest / file.filename, "wb") as f: f.write(await file.read())
    with db() as c: c.execute("UPDATE drops SET uploads=uploads+1 WHERE id=?", (drop_id,)); c.commit()
    return {"status":"ok","saved":file.filename}
