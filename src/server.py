import socket
import threading
from dataclasses import dataclass
from typing import cast

# TODO: Extract to an environment file (#2)
HOST = ""
PORT = 3000


lobby_waiting_lock = threading.Lock()
waiting_player: WaitingPlayer | None = None


@dataclass
class WaitingPlayer:
    conn: socket.socket
    username: str


def send(conn: socket.socket, message: str) -> None:
    try:
        conn.sendall((message + "\n").encode())
    # If the connection no longer exists, we just don't send.
    except BrokenPipeError, OSError:
        pass


def parse_message(line: str) -> tuple[str, list[str]] | None:
    # Convert a command like "JOIN alice" into ["JOIN", "alice"]
    parts = line.strip().split()

    # There was nothing in the line to parse.
    if not parts:
        return None

    # Return (command, arguments). Normalize command as uppercase so we can
    # send "join" as well as "JOIN".
    return parts[0].upper(), parts[1:]


def handle_command_JOIN(conn: socket.socket, args: list[str]) -> None:
    # Use a waiting player state as a global variable. We'll place a waiting
    # player there if not already.
    global waiting_player

    if not args:
        return

    username = args[0]
    player_to_wait = WaitingPlayer(conn, username)
    partner: WaitingPlayer | None = None

    # Acquire the waiting lock, so if two clients JOIN at a close time, they
    # both don't read it as no-one waiting and end up waiting forever.
    with lobby_waiting_lock:
        if waiting_player is None:
            waiting_player = player_to_wait
        else:
            # There was someone waiting, they're our partner and now we're ready
            # to start.
            partner = waiting_player
            waiting_player = None

    if partner is None:
        send(conn, "WAITING")
        return
    else:
        send(partner.conn, f"GAME_START {username}")
        send(conn, f"GAME_START {partner.username}")
        return


def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    global waiting_player

    with conn:
        print(f"Connected from {addr}")

        # Instead of using `recv`, `makefile` will return a file object for the
        # socket. From this, we can read from it as a file and don't have to
        # worry about new lines or other buffer logic.
        #
        # https://docs.python.org/3/library/socket.html#socket.socket.makefile
        # ...compared to...
        # https://docs.python.org/3/library/socket.html#socket.socket.recv
        try:
            reader = conn.makefile("r")

            joined = False

            for line in reader:
                msg = parse_message(line)

                if msg is None:
                    continue

                command, args = msg

                # Don't want them joining twice
                if command == "JOIN" and not joined:
                    joined = True
                    handle_command_JOIN(conn, args)

        # The client can disconnect mid-reading or handling, and can maybe
        # leave a client waiting when they've left.
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"Connection error when handling {addr}: {e}")
        finally:
            # Always check if there's a waiting player, and if it's the one
            # which disconnected, we should remove them so we're not keeping
            # the waiting spot blocked.
            with lobby_waiting_lock:
                if waiting_player is not None and waiting_player.conn is conn:
                    print(
                        f"Waiting player '{waiting_player.username}' disconnected."  # noqa: E501
                    )
                    waiting_player = None


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
