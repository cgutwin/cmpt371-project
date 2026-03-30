from enum import StrEnum


class Command(StrEnum):
    JOIN = "JOIN"
    GUESS = "GUESS"

    # Server-sent commands
    WAITING = "WAITING"
    GAME_START = "GAME_START"
