import socket

import colorama
from colorama import Back, Style, init

colorama.init(autoreset=True)

HOST = "127.0.0.1"
PORT = 3000

NUMBER_OF_GUESSES = 6
GUESS_LENGTH = 5
guess_count = 0
guesses = ["_" * GUESS_LENGTH] * NUMBER_OF_GUESSES

# Array that maps if the letters of the guess are in the word,
# in the wrong order, or not in the word at all.
feedback = ["_" * GUESS_LENGTH] * NUMBER_OF_GUESSES

GREEN = Back.GREEN
YELLOW = Back.YELLOW
GREY = Back.LIGHTBLACK_EX

# Function to colourize guess characters depending on if the guess matches the wordle
# G = correct letter, correct position  (green)
# Y = correct letter, wrong position    (yellow)
# X = letter not in word                (grey)


# e.g. LIGHT against PILOT → X X G X X
# https://www.youtube.com/watch?v=P3AdKGHmtto
def colourize_guess(guess, feedback):
    result = ""
    # Iterate through each character of the word and assign a corresponding colour
    for i in range(GUESS_LENGTH):
        letter = guess[i]
        code = feedback[i]

        if code == "G":
            result += Style.BRIGHT + GREEN + letter
        elif code == "Y":
            result += Style.BRIGHT + YELLOW + letter
        else:
            result += Style.BRIGHT + GREY + letter
    return result


def print_board():
    print(f"Guess number: {guess_count}")
    for i in range(NUMBER_OF_GUESSES):
        if feedback[i] == "_____":
            # Prints an empty row if there has not been a guess yet
            print(f"{guesses[i]}")
        else:
            # colourize each guess with its feedback
            print(f"{colourize_guess(guesses[i], feedback[i])}")
    print("\n")


def client_guess(client):
    global guess_count
    while True:
        client_input = input("Please enter a 5 letter word: ").strip().upper()
        if len(client_input) != 5:
            print("Error: Word must be exactly 5 letters ")
        elif not client_input.isalpha():
            print("Error: Word must only contain letters")
        else:
            # Stores current guess in guesses array and increments guess_count
            guesses[guess_count] = client_input
            guess_count += 1
            break
    client.sendall(f"GUESS {client_input}\n".encode("utf-8"))


def start_client():

    player_name = input("Please enter your name: ")

    # Initializes a socket, AF_INET -> IPV4, SOCK_STREAM -> TCP Protocol
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Reference: https://stackoverflow.com/questions/38544493/python-socket-programming-exception-handling/38545213#38545213
    try:
        client.connect((HOST, PORT))

        client.sendall(f"JOIN {player_name}\n".encode("utf-8"))
        print(f"{player_name} connected. Waiting for opponent")

        reader = client.makefile("r")

        for line in reader:
            line = line.strip()
            if not line:
                continue

            # https://www.geeksforgeeks.org/python/python-string-split/
            parts = line.split()
            command = parts[0]
            # If server sends more than 1 argument, succeeding arguments are stored in a list
            args = parts[1:]

            if command == "GAME_START":
                print(f"Game started! Your opponent is {args[0]}")
                print_board()

                # Function to receive input from user first argument should be command
                client_guess(client)

            elif command == "INVALID_GUESS":
                global guess_count
                print(f"Invalid Guess {args[0]}")

                # if a invalid guess was made it will reset the last guess and decrement guess_count
                guesses[guess_count - 1] = "_____"
                guess_count -= 1

                # Asks client to send another guess due to invalid input
                client_guess(client)

            elif command == "GUESS_RESULT":
                # Stores the guess_result data passed from the server in feedback array
                feedback[guess_count - 1] = args[0]
                print_board()
                # Don't prompt for another guess if the player just solved the
                # word or exhausted all guesses — GAME_OVER is coming next.
                if args[0] != "GGGGG" and guess_count < NUMBER_OF_GUESSES:
                    client_guess(client)

            # elif command == "OPPONENT_PROGRESS":
            #     opponent_count = args[0]
            #     print(f"Opponent's guess count: {opponent_count}")

            # elif command == "OPPONENT_SOLVED":
            #     print("Opponent has solved the puzzle!")

            elif command == "GAME_OVER":
                result = args[0]
                player_time = args[1]
                opponent_time = args[2]
                print(f"\n=== GAME OVER ===")
                print(f"You {result} !")
                print(f"Your time: {player_time}")
                print(f"Opponent time: {opponent_time}")
                break

    except ConnectionRefusedError:
        # Server is not running or unreachable
        print("Could not connect to server. Make sure that it is running!")

    except socket.error as e:
        # Any other socket errors that occurs
        print(f"Network error: {e}")

    finally:
        client.close()


def main() -> None:
    print("client")


# Temp function
def test_print_board():
    global guesses, feedback
    guesses = ["CRANE", "PLANT", "GREAT", "WRONG", "_____", "_____"]
    feedback = ["GYXGX", "XXYXX", "GGGGG", "XXXXX", "_____", "_____"]
    print("Testing...")
    print_board()


if __name__ == "__main__":
    # test_print_board()
    start_client()
    # main()
