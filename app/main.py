"""FastAPI application: movie watchlist CRUD endpoints."""

from fastapi import FastAPI, HTTPException, status

from app import storage
from app.models import MovieCreate, MovieRead, MovieUpdate

app = FastAPI(title="Movie Watchlist", version="0.1.0")


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
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@app.patch("/movies/{movie_id}", response_model=MovieRead)
def update_movie(movie_id: int, data: MovieUpdate) -> MovieRead:
    movie = storage.update(movie_id, data)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@app.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int) -> None:
    if not storage.delete(movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")
