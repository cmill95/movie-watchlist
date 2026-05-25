"""FastAPI application: movie watchlist CRUD endpoints."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import storage
from app.models import MovieCreate, MovieRead, MovieStatus, MovieUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the database schema exists.
    storage.init_db()
    yield
    # Shutdown: nothing to clean up for SQLite (connections are per-request).


app = FastAPI(title="Movie Watchlist", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# --- HTML/HTMX Endpoints


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    movies = storage.list_all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"movies": movies},
    )


@app.get("/ui/movies/{movie_id}", response_class=HTMLResponse)
def ui_get_movie(request: Request, movie_id: int):
    movie = storage.get(movie_id)
    if movie is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return templates.TemplateResponse(
        request=request,
        name="_movie_row.html",
        context={"movie": movie},
    )


@app.get("/ui/movies/{movie_id}/edit", response_class=HTMLResponse)
def ui_edit_movie_form(request: Request, movie_id: int):
    movie = storage.get(movie_id)
    if movie is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return templates.TemplateResponse(
        request=request,
        name="_movie_row_edit.html",
        context={"movie": movie},
    )


@app.delete("/ui/movies/{movie_id}")
def ui_delete_movie(movie_id: int):
    if not storage.delete(movie_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return Response(status_code=http_status.HTTP_200_OK)


@app.post("/ui/movies")
def ui_create_movie(
    request: Request,
    title: Annotated[str, Form()],
    year: Annotated[int | None, Form()] = None,
    status: Annotated[MovieStatus, Form()] = MovieStatus.TO_WATCH,
    rating: Annotated[int | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    data = MovieCreate(
        title=title,
        year=year,
        status=status,
        rating=rating,
        notes=notes,
    )
    movie = storage.create(data)
    return templates.TemplateResponse(
        request=request,
        name="_movie_row.html",
        context={"movie": movie},
    )


@app.patch("/ui/movies/{movie_id}", response_class=HTMLResponse)
def ui_update_movie(
    request: Request,
    movie_id: int,
    title: Annotated[str, Form()],
    year: Annotated[int | None, Form()] = None,
    status: Annotated[MovieStatus, Form()] = MovieStatus.TO_WATCH,
    rating: Annotated[int | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    data = MovieUpdate(
        title=title,
        year=year,
        status=status,
        rating=rating or None,
        notes=notes or None,
    )
    movie = storage.update(movie_id, data)
    if movie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return templates.TemplateResponse(
        request=request,
        name="_movie_row.html",
        context={"movie": movie},
    )


# ---- JSON Endpoints


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/movies", response_model=MovieRead, status_code=http_status.HTTP_201_CREATED)
def create_movie(data: MovieCreate) -> MovieRead:
    return storage.create(data)


@app.get("/movies", response_model=list[MovieRead])
def list_movies() -> list[MovieRead]:
    return storage.list_all()


@app.get("/movies/{movie_id}", response_model=MovieRead)
def get_movie(movie_id: int) -> MovieRead:
    movie = storage.get(movie_id)
    if movie is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.patch("/movies/{movie_id}", response_model=MovieRead)
def update_movie(movie_id: int, data: MovieUpdate) -> MovieRead:
    movie = storage.update(movie_id, data)
    if movie is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.delete("/movies/{movie_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int) -> None:
    if not storage.delete(movie_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
