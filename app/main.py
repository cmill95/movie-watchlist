"""FastAPI application: movie watchlist CRUD endpoints."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import TypeAdapter, ValidationError
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.models import (
    MovieCreate,
    MovieRead,
    MovieStatus,
    MovieUpdate,
    Name,
    Notes,
    Password,
    Rating,
    Title,
    User,
    Year,
)
from app.security import hash_password, verify_password
from app.storage import (
    DEFAULT_USER_ID,
    DuplicateUserName,
    MovieRepository,
    dispose_engine,
    init_storage,
    make_repository,
)

# Validates a submitted password against the Password constraints (length),
# reusing the model definition rather than duplicating the bounds in the route.
_password_adapter = TypeAdapter(Password)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the configured backend's schema exists.
    init_storage()
    yield
    dispose_engine()
    # Shutdown: nothing to clean up for SQLite (connections are per-request).


def get_current_user(request: Request) -> int:
    """Current user id from the signed session, or the default user if none.

    The session cookie is signed (SessionMiddleware), so the id can't be forged;
    it's only ever written by switch_user/add_user after any password check."""
    user_id = request.session.get("user_id")
    return user_id if isinstance(user_id, int) else DEFAULT_USER_ID


def get_repository(user_id: Annotated[int, Depends(get_current_user)]) -> MovieRepository:
    return make_repository(user_id)


def get_users() -> list[User]:
    return make_repository(DEFAULT_USER_ID).list_users()


app = FastAPI(title="Movie Watchlist", version="0.1.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=get_settings().session_secret)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Repository injected per request. FastAPI resolves get_repository once
# because it is lru_cached
RepoDep = Annotated[MovieRepository, Depends(get_repository)]

UsersDep = Annotated[list[User], Depends(get_users)]


# --- HTML/HTMX Endpoints


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    repo: RepoDep,
    users: UsersDep,
    current_user_id: Annotated[int, Depends(get_current_user)],
):
    movies = repo.list_all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"movies": movies, "users": users, "current_user_id": current_user_id},
    )


@app.post("/ui/switch-user")
def switch_user(
    request: Request,
    user_id: Annotated[int, Form()],
    # Raw string, not the Password type: a wrong login shouldn't fail validation
    # (422) on length — it should fail the password check (401).
    password: Annotated[str | None, Form()] = None,
) -> Response:
    admin = make_repository(DEFAULT_USER_ID)
    user = admin.get_user(user_id)
    if user is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.has_password:
        stored = admin.get_password_hash(user_id)
        if stored is None or password is None or not verify_password(password, stored):
            raise HTTPException(http_status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    request.session["user_id"] = user_id
    return Response(headers={"HX-Redirect": "/"})


@app.post("/ui/users")
def add_user(
    request: Request,
    name: Annotated[Name, Form()],
    # Optional: an empty field arrives as "" (not absent), so treat blank as
    # "no password". A non-blank value is validated against the Password type.
    password: Annotated[str | None, Form()] = None,
) -> Response:
    password_hash = None
    if password:
        try:
            valid = _password_adapter.validate_python(password)
        except ValidationError as exc:
            raise HTTPException(
                http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()
            ) from None
        password_hash = hash_password(valid)
    try:
        user = make_repository(DEFAULT_USER_ID).create_user(name, password_hash=password_hash)
    except DuplicateUserName:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT, detail="That name is already taken"
        ) from None
    request.session["user_id"] = user.id
    return Response(headers={"HX-Redirect": "/"})


@app.get("/ui/users/{user_id}", response_class=HTMLResponse)
def ui_get_user(request: Request, user_id: int):
    user = make_repository(DEFAULT_USER_ID).get_user(user_id)
    if user is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="User not found")
    return templates.TemplateResponse(
        request=request, name="_user_name.html", context={"current_user": user}
    )


@app.get("/ui/users/{user_id}/edit", response_class=HTMLResponse)
def ui_edit_user_form(request: Request, user_id: int):
    user = make_repository(DEFAULT_USER_ID).get_user(user_id)
    if user is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="User not found")
    return templates.TemplateResponse(
        request=request, name="_user_name_edit.html", context={"current_user": user}
    )


@app.patch("/ui/users/{user_id}")
def rename_user(user_id: int, name: Annotated[Name, Form()]) -> Response:
    try:
        renamed = make_repository(DEFAULT_USER_ID).rename_user(user_id, name)
    except DuplicateUserName:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT, detail="That name is already taken"
        ) from None
    if renamed is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(headers={"HX-Redirect": "/"})


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
