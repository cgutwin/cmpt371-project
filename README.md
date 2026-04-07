# CMPT371 Assignment 3 — Multiplayer Wordle

![Playing the Wordle in two terminal sessions with a server](header_preview.png)

**Course:** CMPT 371 — Data Communications & Networking

**Instructor:** Mirza Zaeem Baig

**Semester:** Spring 2026

## Group Members

| Name | Student ID | Email |
| :---- | :---- | :---- |
| Chris Gutwin | 301400079 | cgutwin@sfu.ca |
| Matthew Tortolano | | |

## Project Description

Play a game of Wordle with others! Pair up with another player and see who can solve the puzzle the fastest!

## Limitations

- Clients connect to and play on the localhost machine.
- Closing the server can leave clients with an open connection to nowhere.
- Clients disconnecting may not leave the game session and it won't end.
  - Windows may not play nice with \<Control-C\> and the terminal session should be closed to quit.
- Can only play one game before needing to reconnect and join another lobby.

## Installation Guide

This project used Python 3.14. 

Clone the repository to a place of your choosing:
```sh
git clone https://github.com/cgutwin/cmpt371-project.git dir
cd dir
```

Create a virtual environment and install dependencies:

```sh
python -m venv .venv
```

Activate the virtual environment:

```sh
source .venv/Scripts/activate       # bash/zsh (Windows)
source .venv/bin/activate           # bash/zsh (Mac/Linux)
source .venv/Scripts/activate.fish  # fish (Windows)
source .venv/bin/activate.fish      # fish (Mac/Linux)
.\.venv\Scripts\Activate.ps1        # PowerShell (Windows)
```

Install dependencies:

```sh
pip install -r requirements.txt
```

## Running

### Start the Server

Open a terminal session in the project folder. The server will bind to `127.0.0.1` on port `3000`.
```sh
python src/server.py
```

### Connect Player One

In a new terminal window/session, run the client script. Enter your username, and you'll be placed in the waiting lobby until another player joins to make a pair.

```sh
python src/client.py
```

### Connect Player Two
In another new terminal session, run the client script again. Enter your username and you will be paired with Player One. The match, and timer, begins immediately!


```sh
python src/client.py
```

### Gameplay

- The server will randomly choose a word to guess.
- You will be prompted to enter a guess word.
- Each player can make guesses simultaneously.
- If the guess isn't a guessable word, or is too short, you will be informed and told to make another guess.
- The server will validate your guess based on the randomly chosen word, and return back a colour encoding for your guess.
- When one player guesses the word, they will wait for the other to either guess, or run out of guesses, before revealing the winner and time.

## Technical Protocol Details

- **Message Format:** `COMMAND message` (for example: `GUESS crane` may return `GUESS_RESULT GGXYX`)
- **Joining a Game:** `JOIN username` will join the game lobby. If another player hasn't joined, the server sends back `WAITING`. When another player joins, the server manages the game session and sends back `GAME_START` to each client in the game.
- **Gameplay:** Clients are responsible for submitting words with `GUESS <word>`, and the server is responsbible for checking if the guess matches the chosen word, sending back the colour encoding `GUESS_RESULT GGXYX`. When a player solves and the other runs out of guesses, or both run out of guesses, `GAME_OVER` is sent with results of the game to each client.

## References

- Socket boilerplate was taken from the Python documentation on sockets, available at https://docs.python.org/3/library/socket.html#example.

## Development

Create a virtual environment with `python -m venv .venv` as above, activate, and run `pip install -r requirements-dev.txt -r requirements.txt`.


### Available Tools
Run tests:

```sh
python -m pytest
```

Run linter:

```sh
python -m ruff check src tests
```

Run type checker:

```sh
python -m mypy src
```

Format code:

```sh
python -m ruff format src tests
```
