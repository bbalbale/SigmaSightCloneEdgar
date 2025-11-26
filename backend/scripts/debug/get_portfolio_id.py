import hashlib
from uuid import UUID

def generate_deterministic_uuid(seed_string: str) -> UUID:
    hash_hex = hashlib.md5(seed_string.encode()).hexdigest()
    return UUID(hash_hex)

print(generate_deterministic_uuid("demo_individual@sigmasight.com_portfolio"))
