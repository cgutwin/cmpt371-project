import signal
import socket
import sys
import threading
from pathlib import Path
from typing import cast

from server.game_session import GameSession
from server.player import Player

# TEMP fix to solve Zed debugger not finding module on Linux
sys.path.insert(0, str(Path(__file__).parent))

from protocol_commands import Command, InvalidGuessReason

HOST = ""
PORT = 3000
MAX_GUESSES = 6


# https://stackoverflow.com/questions/17174001/stop-pyzmq-receiver-by-keyboardinterrupt/26392777#26392777
signal.signal(signal.SIGINT, signal.SIG_DFL)


def send(conn: socket.socket, message: str) -> None:
    try:
        conn.sendall((message + "\n").encode())
    # If the connection no longer exists, we just don't send.
    except BrokenPipeError, OSError:
        pass


class GameLobby:
    def __init__(self) -> None:
        self._waiting: Player | None = None
        self._lock: threading.Lock = threading.Lock()

    def join_game(self, player: Player) -> Player | None:
        print(
            f"Joining player {player.username} from {player.conn.getpeername()}."  # noqa: E501
        )
        with self._lock:
            if self._waiting is None:
                self._waiting = player
                return None

            opponent = self._waiting
            self._waiting = None
            return opponent

    def remove_player_from_waiting(self, player: Player) -> None:
        with self._lock:
            if self._waiting is player:
                self._waiting = None


lobby = GameLobby()
active_games: dict[str, GameSession] = {}


def parse_message(line: str) -> tuple[Command, list[str]] | None:
    # Convert a command like "JOIN alice" into ["JOIN", "alice"]
    parts = line.strip().split()

    # There was nothing in the line to parse.
    if not parts:
        return None

    try:
        # Conform the command part to the command enum, which will automatically
        # reject invalid commands.
        command = Command(parts[0])
    except ValueError:
        return None

    # Return (command, arguments).
    return command, parts[1:]


def handle_command_GUESS(player: Player, args: list[str]) -> None:
    if args[0].lower() not in ["a"]:
        send(
            player.conn,
            f"{Command.INVALID_GUESS} {InvalidGuessReason.NOT_A_WORD}",
        )
        return

    if not active_games[player.username] or not args:
        return

    session = active_games[player.username]

    if session.state[player.username].guess_count >= MAX_GUESSES:
        return

    opponent = session.get_player_opponent(player)
    guess_result = session.handle_guess(player, args[0])

    if guess_result is None:
        send(
            player.conn,
            f"{Command.INVALID_GUESS} {InvalidGuessReason.WRONG_LENGTH}",
        )
        return

    guess_feedback, guess_count = guess_result

    send(player.conn, f"{Command.GUESS_RESULT} {guess_feedback}")
    send(
        opponent.conn,
        f"{Command.OPPONENT_PROGRESS} {guess_count}",
    )

    if guess_feedback == "GGGGG":
        session.mark_player_has_solved(player)
        send(
            opponent.conn,
            f"{Command.OPPONENT_SOLVED}",
        )

    if (
        session.state[opponent.username].guess_count >= MAX_GUESSES
        or guess_feedback == "GGGGG"
    ):
        # Check if opponent is also done
        opp_count = session.state[opponent.username].guess_count
        opp_solved = session.state[opponent.username].solve_time is not None
        if opp_solved or opp_count >= MAX_GUESSES:
            if session.try_end():
                for p in (player, opponent):
                    send(
                        p.conn,
                        f"{Command.GAME_OVER} {session.get_player_result(player)} {session.state[player.username].solve_time} {session.state[opponent.username].solve_time}",  # noqa: E501
                    )


def handle_command_JOIN(player: Player, args: list[str]) -> Player | None:
    if not args:
        return

    player.username = args[0]

    partner: Player | None = lobby.join_game(player=player)

    if partner is None:
        send(player.conn, "WAITING")
        return
    else:
        return partner


def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    # Instead of using `recv`, `makefile` will return a file object for the
    # socket. From this, we can read from it as a file and don't have to
    # worry about new lines or other buffer logic.
    #
    # https://docs.python.org/3/library/socket.html#socket.socket.makefile
    # ...compared to...
    # https://docs.python.org/3/library/socket.html#socket.socket.recv
    player = Player(conn, conn.makefile("r"), username="")

    try:
        for line in player.reader:
            msg = parse_message(line)

            if msg is None:
                continue

            command, args = msg

            if command == Command.JOIN:
                partner = handle_command_JOIN(player=player, args=args)

                # If when joining, we have a partner, we're ready to start the game.  # noqa: E501
                if partner:
                    game = GameSession(players=(player, partner))

                    active_games[player.username] = game
                    active_games[partner.username] = game

                    # Should be sending after the game is created instead of just when joining.  # noqa: E501
                    send(partner.conn, f"GAME_START {player.username}")
                    send(player.conn, f"GAME_START {partner.username}")
            elif command == Command.GUESS:
                handle_command_GUESS(player=player, args=args)

    # The client can disconnect mid-reading or handling, and can maybe
    # leave a client waiting when they've left.
    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print(f"Connection error when handling {addr}: {e}")
    finally:
        # Always check if there's a waiting player, and if it's the one
        # which disconnected, we should remove them so we're not keeping
        # the waiting spot blocked.
        lobby.remove_player_from_waiting(player=player)


def main() -> None:
    # Create a new TCP (SOCK_STREAM) IPv4 (AF_INET) socket.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # REUSEADDR allows the kernel to reuse a local socket without waiting
        # for its timeout state to expire.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)

        print(f"Listening on port {PORT}")

        # Accept clients in a loop and spawn a thread for them: this will be
        # used later because clients will each run their guesses in real-time.
        try:
            while True:
                # Casting to create explicit types for passing.
                # The addr for AF_INET is tuple[str, int] and varies for
                # different protocols.
                result = cast(tuple[socket.socket, tuple[str, int]], s.accept())
                conn, addr = result
                threading.Thread(
                    target=handle_client, args=(conn, addr), daemon=True
                ).start()
        except KeyboardInterrupt:
            s.close()


if __name__ == "__main__":
    main()
