import socket
import threading
from dataclasses import dataclass
from io import TextIOWrapper
from typing import cast

from protocol_commands import Command

HOST = ""
PORT = 3000


@dataclass
class Player:
    conn: socket.socket
    reader: TextIOWrapper
    username: str


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


def send(conn: socket.socket, message: str) -> None:
    try:
        conn.sendall((message + "\n").encode())
    # If the connection no longer exists, we just don't send.
    except BrokenPipeError, OSError:
        pass


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


def handle_command_JOIN(player: Player, args: list[str]) -> None:
    if not args:
        return

    player.username = args[0]

    partner: Player | None = lobby.join_game(player=player)

    if partner is None:
        send(player.conn, "WAITING")
        return
    else:
        send(partner.conn, f"GAME_START {player.username}")
        send(player.conn, f"GAME_START {partner.username}")
        return


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
                handle_command_JOIN(player=player, args=args)
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
