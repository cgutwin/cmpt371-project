from enum import StrEnum


class Command(StrEnum):
    JOIN = "JOIN"
    GUESS = "GUESS"

    # Server-sent commands
    WAITING = "WAITING"
    GAME_START = "GAME_START"
    GUESS_RESULT = "GUESS_RESULT"
    INVALID_GUESS = "INVALID_GUESS"


class InvalidGuessReason(StrEnum):
    INVALID_WORD = "INVALID_WORD"
    WRONG_LENGTH = "WRONG_LENGTH"
