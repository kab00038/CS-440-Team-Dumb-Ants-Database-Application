from argon2 import PasswordHasher, exceptions

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

def hash_password(plain: str) -> str:
    return ph.hash(plain)

def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        return ph.verify(stored_hash, plain)
    except exceptions.VerifyMismatchError:
        return False