import random
import threading
import time
from dataclasses import dataclass

import wordledict
from player import Player


@dataclass
class PlayerState:
    guess_count: int = 0
    solve_time: float | None = None


class GameSession:
    def __init__(self, players: tuple[Player, Player]) -> None:
        self.word: str = "react"
        # self.word: str = random.choice(wordledict.possible_answers)
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
        The player results are based on their time to solve (TTS) the puzzle,
        compared to their opponents TTS.
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

    def handle_guess(
        self, player: Player, guess_word: str
    ) -> tuple[str, int] | None:
        if len(self.word) != len(guess_word):
            return
        # Start with all X in the response
        response = ["X"] * len(self.word)
        unmatched_letters: list[str] = []

        # Look at all pairs of letters in the word and guess
        for i, (w, g) in enumerate(zip(self.word, guess_word, strict=False)):
            # Letters match
            if w == g:
                response[i] = "G"
            # Add letters we haven't matched to our list
            else:
                unmatched_letters.append(w)

        # Look over the guess word again
        for i, (_, g) in enumerate(zip(self.word, guess_word, strict=False)):
            if response[i] == "G":
                continue
            # If the guess letter is in the wrong spot, mark it and move on
            if g in unmatched_letters:
                response[i] = "Y"
                unmatched_letters.remove(g)

        self.state[player.username].guess_count += 1
        return "".join(response), self.state[player.username].guess_count

    def try_end(self) -> bool:
        with self.game_ended_lock:
            if self.game_ended:
                return False
            self.game_ended = True
            return True
