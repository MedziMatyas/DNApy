"""
DNA ladders (size markers for the agarose gel preview).

The ladders that come with the program are in data/dnaLadders.lst. Ladders that the user adds are saved in
dnaLadders.lst in the user's folder (~/.dnapy), because the files of an installed program should not be changed.
Each line is: name,size,size,size,...
"""
import os

from . import DATA_DIR, USER_DIR

BUNDLED_FILE = os.path.join(DATA_DIR, 'dnaLadders.lst')
USER_FILE = os.path.join(USER_DIR, 'dnaLadders.lst')


def _parse(line):
    """['name', size, size, ...] from a line of a ladder file, sizes as integers where possible."""
    parts = []
    for item in line.strip().split(','):
        try:
            parts.append(int(item))
        except ValueError:
            parts.append(item)
    return parts


def load(user_file=None):
    """All ladders, first those that come with the program and then the ones the user added."""
    ladders = []
    for path in (BUNDLED_FILE, user_file or USER_FILE):
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            ladders.extend(_parse(line) for line in f if line.strip())
    return ladders


def add(ladder, user_file=None):
    """Save a ladder, given as ['name', size, size, ...], in the file of the user."""
    path = user_file or USER_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as f:
        f.write(','.join(str(item) for item in ladder) + '\n')
