import random
import string
from faker import Faker

fake = Faker("zh_CN")

_FAKER_MAP = {
    "${random_email}": lambda: fake.email(),
    "${random_first_name}": lambda: fake.first_name(),
    "${random_last_name}": lambda: fake.last_name(),
    "${random_name}": lambda: fake.name(),
    "${random_address}": lambda: fake.address(),
    "${random_phone}": lambda: fake.phone_number(),
    "${random_password}": lambda: _random_password(),
    "${random_int}": lambda: str(random.randint(1, 99999)),
    "${random_price}": lambda: str(random.randint(100, 99999)),
    "${random_string}": lambda: "".join(random.choices(string.ascii_lowercase, k=8)),
}


def _random_password():
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    rest = "".join(random.choices(string.ascii_letters + string.digits, k=5))
    return f"{upper}{lower}{digit}{rest}@{random.randint(10, 99)}"


def resolve_faker(value):
    if not isinstance(value, str):
        return value
    for placeholder, generator in _FAKER_MAP.items():
        if placeholder in value:
            return value.replace(placeholder, generator())
    return value


def register_faker(placeholder, generator):
    _FAKER_MAP[placeholder] = generator
