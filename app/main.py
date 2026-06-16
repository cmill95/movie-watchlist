"""FastAPI application: movie watchlist CRUD endpoints."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import MovieCreate, MovieRead, MovieStatus, MovieUpdate, Notes, Rating, Title, Year
from app.storage import (
    DEFAULT_USER_ID,
    MovieRepository,
    dispose_engine,
    init_storage,
    make_repository,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the configured backend's schema exists.
    init_storage()
    yield
    dispose_engine()
    # Shutdown: nothing to clean up for SQLite (connections are per-request).


def get_current_user(user_id: Annotated[str | None, Cookie()] = None) -> int:
    """Current user id from the `user_id` cookie. Unverified at this point."""
    if user_id is None:
        return DEFAULT_USER_ID
    try:
        return int(user_id)
    except ValueError:
        return DEFAULT_USER_ID


def get_repository(user_id: Annotated[int, Depends(get_current_user)]) -> MovieRepository:
    return make_repository(user_id)


app = FastAPI(title="Movie Watchlist", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Repository injected per request. FastAPI resolves get_repository once
# because it is lru_cached
RepoDep = Annotated[MovieRepository, Depends(get_repository)]


# --- HTML/HTMX Endpoints


@app.get("/", response_class=HTMLResponse)
def index(request: Request, repo: RepoDep):
    movies = repo.list_all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"movies": movies},
    )


@app.get("/ui/movies/{movie_id}", response_class=HTMLResponse)
def ui_get_movie(request: Request, movie_id: int, repo: RepoDep):
    movie = repo.get(movie_id)
    if movie is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return templates.TemplateResponse(
        request=request,
        name="_movie_row.html",
        context={"movie": movie},
    )


@app.get("/ui/movies/{movie_id}/edit", response_class=HTMLResponse)
def ui_edit_movie_form(request: Request, movie_id: int, repo: RepoDep):
    movie = repo.get(movie_id)
    if movie is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return templates.TemplateResponse(
        request=request,
        name="_movie_row_edit.html",
        context={"movie": movie},
    )


@app.delete("/ui/movies/{movie_id}")
def ui_delete_movie(movie_id: int, repo: RepoDep):
    if not repo.delete(movie_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return Response(status_code=http_status.HTTP_200_OK)


@app.post("/ui/movies")
def ui_create_movie(
    request: Request,
    repo: RepoDep,
    title: Annotated[Title, Form()],
    year: Annotated[Year | None, Form()] = None,
    status: Annotated[MovieStatus, Form()] = MovieStatus.TO_WATCH,
    rating: Annotated[Rating | None, Form()] = None,
    notes: Annotated[Notes | None, Form()] = None,
):
    data = MovieCreate(
        title=title,
        year=year,
        status=status,
        rating=rating,
        notes=notes,
    )
    movie = repo.create(data)
    return templates.TemplateResponse(
        request=request,
        name="_movie_row.html",
        context={"movie": movie},
    )


@app.patch("/ui/movies/{movie_id}", response_class=HTMLResponse)
def ui_update_movie(
    request: Request,
    movie_id: int,
    repo: RepoDep,
    title: Annotated[Title, Form()],
    year: Annotated[Year | None, Form()] = None,
    status: Annotated[MovieStatus, Form()] = MovieStatus.TO_WATCH,
    rating: Annotated[Rating | None, Form()] = None,
    notes: Annotated[Notes | None, Form()] = None,
):
    data = MovieUpdate(title=title, year=year, status=status, rating=rating, notes=notes)
    movie = repo.update(movie_id, data)
    if movie is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return templates.TemplateResponse(
        request=request, name="_movie_row.html", context={"movie": movie}
    )


# ---- JSON Endpoints


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/movies", response_model=MovieRead, status_code=http_status.HTTP_201_CREATED)
def create_movie(data: MovieCreate, repo: RepoDep) -> MovieRead:
    return repo.create(data)


@app.get("/movies", response_model=list[MovieRead])
def list_movies(repo: RepoDep) -> list[MovieRead]:
    return repo.list_all()


@app.get("/movies/{movie_id}", response_model=MovieRead)
def get_movie(movie_id: int, repo: RepoDep) -> MovieRead:
    movie = repo.get(movie_id)
    if movie is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.patch("/movies/{movie_id}", response_model=MovieRead)
def update_movie(movie_id: int, data: MovieUpdate, repo: RepoDep) -> MovieRead:
    movie = repo.update(movie_id, data)
    if movie is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.delete("/movies/{movie_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int, repo: RepoDep) -> None:
    if not repo.delete(movie_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Movie not found")
