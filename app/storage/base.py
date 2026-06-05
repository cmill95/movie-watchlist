"""Repository interface for movie storage.

The contract the route layer depends on. Concrete backends (stdlib sqlite3,
SQLAlchemy ORM) satisfy this protocol; FastAPI injects whichever one the
MOVIES_BACKEND setting selects.

Only the operations the routes actually call live here. Schema setup and
test reset are deliberately not on this protocol — they're lifecycle/test
concerns, handled per-backend at the factory/fixture layer (step 3).
"""

from typing import Protocol

from app.models import MovieCreate, MovieRead, MovieUpdate


class MovieRepository(Protocol):
    def create(self, data: MovieCreate) -> MovieRead: ...
    def get(self, movie_id: int) -> MovieRead | None: ...
    def list_all(self) -> list[MovieRead]: ...
    def update(self, movie_id: int, data: MovieUpdate) -> MovieRead | None: ...
    def delete(self, movie_id: int) -> bool: ...
