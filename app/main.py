"""FastAPI application: movie watchlist CRUD endpoints."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import storage
from app.models import MovieCreate, MovieRead, MovieUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the database schema exists.
    storage.init_db()
    yield
    # Shutdown: nothing to clean up for SQLite (connections are per-request).


app = FastAPI(title="Movie Watchlist", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    movies = storage.list_all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"movies": movies},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/movies", response_model=MovieRead, status_code=status.HTTP_201_CREATED)
def create_movie(data: MovieCreate) -> MovieRead:
    return storage.create(data)


@app.get("/movies", response_model=list[MovieRead])
def list_movies() -> list[MovieRead]:
    return storage.list_all()


@app.get("/movies/{movie_id}", response_model=MovieRead)
def get_movie(movie_id: int) -> MovieRead:
    movie = storage.get(movie_id)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.patch("/movies/{movie_id}", response_model=MovieRead)
def update_movie(movie_id: int, data: MovieUpdate) -> MovieRead:
    movie = storage.update(movie_id, data)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int) -> None:
    if not storage.delete(movie_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Movie not found")
