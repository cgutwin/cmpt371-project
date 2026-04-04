import threading
import time
from dataclasses import dataclass

from server.player import Player


@dataclass
class PlayerState:
    guess_count: int = 0
    solve_time: float | None = None


class GameSession:
    def __init__(self, players: tuple[Player, Player]) -> None:
        # TODO: Add word list and random word grabber
        self.word: str = "react"
        self.players: tuple[Player, Player] = players
        self.state: dict[str, PlayerState] = {
            p.username: PlayerState() for p in players
        }
        self.game_start_time: float = time.monotonic()
        self.game_ended_lock: threading.Lock = threading.Lock()
        self.game_ended: bool = False

    def get_player_opponent(self, player: Player) -> Player:
        """
        Gets the opponent Player object for the specified player.
        """
        if player is self.players[0]:
            return self.players[1]
        else:
            return self.players[0]

    def mark_player_has_solved(self, player: Player) -> None:
        self.state[player.username].solve_time = (
            time.monotonic() - self.game_start_time
        )

    def get_player_result(self, player: Player) -> str:
        """
        The player results are based on their time to solve (TTS) the puzzle, compared
        to their opponents TTS.
        """
        player_solve_time = self.state[player.username].solve_time

        opponent = self.get_player_opponent(player)
        opponent_solve_time = self.state[opponent.username].solve_time

        if player_solve_time is None and opponent_solve_time is None:
            return "DRAW"
        if player_solve_time is None:
            return "LOSE"
        if opponent_solve_time is None:
            return "WIN"
        if player_solve_time < opponent_solve_time:
            return "WIN"
        if opponent_solve_time < player_solve_time:
            return "LOSE"
        return "DRAW"

    # https://stackoverflow.com/questions/76915922/python-comparison-problem-for-wordle-type-game
    def handle_guess(
        self, player: Player, guess_word: str
    ) -> tuple[str, int] | None:
        response = ""
        word_letters = list(self.word.lower())

        try:
            for a, b in zip(self.word, guess_word, strict=True):
                if b in word_letters:
                    response += "G" if a == b else "Y"
                    word_letters.remove(b)
                else:
                    response += "X"

        except ValueError:
            print("guess is not equal size of the word.")
            return

        self.state[player.username].guess_count += 1
        return response, self.state[player.username].guess_count

    def try_end(self) -> bool:
        with self.game_ended_lock:
            if self.game_ended:
                return False
            self.game_ended = True
            return True
