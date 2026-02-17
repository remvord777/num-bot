from datetime import datetime


def reduce_number(n: int) -> int:
    while n > 9 and n not in (11, 22):
        n = sum(int(d) for d in str(n))
    return n


def life_path(day: int, month: int, year: int) -> int:
    total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
    return reduce_number(total)


def personal_year(day: int, month: int) -> int:
    current_year = datetime.now().year
    total = sum(int(d) for d in f"{day:02d}{month:02d}{current_year}")
    return reduce_number(total)
