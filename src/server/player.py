from dataclasses import dataclass
from io import TextIOWrapper
from socket import socket


@dataclass
class Player:
    conn: socket
    reader: TextIOWrapper
    username: str
