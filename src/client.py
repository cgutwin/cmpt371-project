import socket
import colorama
import re
from colorama import Back, Fore, Style, init
from protocol_commands import Command

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

# Returns the set of used letters guessed by the player
def get_used_letters():
    used = set()
    for guess in guesses:
        if guess != "_" * GUESS_LENGTH:
            used.update(guess)
    return used

# returns the set of letters that were in the wordle from the guessed word
def get_correct_letters():
    correct = set()
    for i in range(guess_count):
        if feedback[i] != "_" * GUESS_LENGTH:
            for j in range(GUESS_LENGTH):
                if feedback[i][j] in ["G", "Y"]:
                    correct.add(guesses[i][j])
    return correct

# Centers the guesses of the colourized guesses
# Copilot assisted here due to center() function not working with colourized characters 
def center_coloured_text(text, width):
    # Remove ANSI codes to calculate visible length
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    visible_length = len(ansi_escape.sub('', text))

    padding = (width - visible_length) // 2
    return " " * padding + text

# Displays game board
# CoPilot helped with the layout of the game board
def print_board():
    width = 50
    
    print("\n" + "="*width)
    print("WORDLE GAME".center(width))
    print("="*width)
    
    # Prints the stats 
    remaining = NUMBER_OF_GUESSES - guess_count
    stats = f"Guess: {guess_count}/{NUMBER_OF_GUESSES} | Remaining: {remaining}"
    print(stats.center(width))
    print("-"*width)
    
    # Prints the guesses
    for i in range(NUMBER_OF_GUESSES):
        if feedback[i] == "_____":
            print(guesses[i].center(width))
        else:
            coloured = colourize_guess(guesses[i], feedback[i])
            print(center_coloured_text(coloured, width))
    
    # Prints which letters have been used and which ones are correct
    print("-"*width)
    used_letters = get_used_letters()
    correct_letters = get_correct_letters()
    
    letters_text = f"Letters: {', '.join(sorted(used_letters)) if used_letters else 'None'}"
    print(letters_text.center(width))
    
    if correct_letters:
        correct_text = f"Correct: {Style.BRIGHT + Fore.GREEN + ', '.join(sorted(correct_letters)) + Style.RESET_ALL}"
        print(correct_text.center(width))
    
    print("="*width + "\n")


def client_guess(client):
    global guess_count
    while True:
        client_input = input("Please enter a 5 letter word: ").strip().upper()
        if len(client_input) != GUESS_LENGTH:
            print("Error: Word must be exactly 5 letters ")

        elif not client_input.isalpha():
            print("Error: Word must only contain letters")

        else:
            # Stores current guess in guesses array and increments guess_count
            guesses[guess_count] = client_input
            guess_count += 1
            break
    client.sendall(f"{Command.GUESS} {client_input}\n".encode("utf-8"))


def start_client():

    player_name = input("Please enter your name: ")

    # Initializes a socket, AF_INET -> IPV4, SOCK_STREAM -> TCP Protocol
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Reference: https://stackoverflow.com/questions/38544493/python-socket-programming-exception-handling/38545213#38545213
    try:
        client.connect((HOST, PORT))

        client.sendall(f"{Command.JOIN} {player_name}\n".encode("utf-8"))
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

            if command == Command.GAME_START:
                global opponent_name
                opponent_name = args[0]
                print(f"Game started! Your opponent is {args[0]}")
                
                print_board()

                # Function to receive input from user first argument should be command
                client_guess(client)

            elif command == Command.INVALID_GUESS:
                global guess_count
                print(f"Invalid Guess {args[0]}")

                # if a invalid guess was made it will reset the last guess and decrement guess_count
                guesses[guess_count - 1] = "_____"
                guess_count -= 1

                # Asks client to send another guess due to invalid input
                client_guess(client)

            elif command == Command.GUESS_RESULT:
                # Stores the guess_result data passed from the server in feedback array
                feedback[guess_count - 1] = args[0]
                print_board()
                # Don't prompt for another guess if the player just solved the
                # word or exhausted all guesses — GAME_OVER is coming next.
                if args[0] != "GGGGG" and guess_count < NUMBER_OF_GUESSES:
                    client_guess(client)

            elif command == Command.GAME_OVER:
                result = args[0]
                player_time = float(args[1])
                opponent_time = float(args[2])
                
                width = 50
 
                print("\n" + "="*width)
                print(f"  GAME OVER - YOU {result.upper()}!".center(48))
                print("="*width)
                
                if result.upper() == "WIN":
                    if player_time < opponent_time:
                        seconds_ahead = opponent_time - player_time
                        print(f"You beat {opponent_name} by {seconds_ahead:.1f} seconds!")

                elif result.upper() == "LOSE":
                    seconds_behind = player_time - opponent_time
                    print(f"{opponent_name} beat you by {seconds_behind:.1f} seconds")

                else:
                    print(f"Tie with {opponent_name}! Both players took the same time.")
                
                print(f"\n  Your time:      {player_time:.1f}s")
                print(f"  Opponent time:  {opponent_time:.1f}s\n")
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





if __name__ == "__main__":
    start_client()
    # main()