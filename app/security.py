"""Password hashing helpers.

Wraps bcrypt so the storage and route layers never touch it directly. Hashes
are stored as UTF-8 strings (bcrypt works in bytes); we encode/decode at this
boundary.
"""

import bcrypt

# bcrypt only considers the first 72 bytes of a password. We reject longer
# inputs at the model layer (models.Password) rather than silently truncating.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
