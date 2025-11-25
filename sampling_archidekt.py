import utils
import random
from loguru import logger
from tqdm.notebook import tqdm

def main(*args, **kwargs):
    ntimes = int(args[0])
    for index in tqdm(range(ntimes)):
        current = random.randint(0, 19999999)
        try:
            logger.debug(f"Tentando baixar deck: {current}")
            utils.get_deck_by_id(current, 'data')
        except Exception as e:
            logger.debug(f"Erro: {e}")
            continue


if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])