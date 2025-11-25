import pandas as pd
from pyrchidekt.api import getDeckById
from utils import get_deck_by_id
import argparse
from loguru import logger

def main(*args, **kwargs):
    print(args)
    for deck_id in args: # passa lista de deck_ids para download em args
        print(deck_id)
        get_deck_by_id(deck_id, save_path='.')

if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])
