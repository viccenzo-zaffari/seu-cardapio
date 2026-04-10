from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base
import routes_auth
import routes_cardapio
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Seu Cardapio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/api")
app.include_router(routes_cardapio.router, prefix="/api")

frontend_path = os.path.join(os.path.dirname(__file__), "..")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def root():
    return FileResponse(os.path.join(frontend_path, "login.html"))

@app.get("/login")
def login_page():
    return FileResponse(os.path.join(frontend_path, "login.html"))

@app.get("/painel")
def painel_page():
    return FileResponse(os.path.join(frontend_path, "painel-admin.html"))

@app.get("/cardapio/{slug}")
def cardapio_page(slug: str):
    return FileResponse(os.path.join(frontend_path, "cardapio-publico.html"))

@app.get("/health")
def health():
    return {"status": "healthy"}