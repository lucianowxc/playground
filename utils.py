import pandas as pd
from pyrchidekt.api import getDeckById
from pyedhrec import EDHRec
import scrython
from loguru import logger

def get_deck_by_id(deck_id, save_path=None):
    deck = getDeckById(deck_id)
    deck_cards = pd.DataFrame([
        {
            'deck_name': deck.name,
            'name': card.card.oracle_card.name,
            'mana_cost': card.card.oracle_card.mana_cost,
            'types': card.card.oracle_card.types[0],
            'default_category': card.card.oracle_card.default_category,
            'cmc': card.card.oracle_card.cmc,
            # 'text': card.card.oracle_card.text,
            'cost': card.card.prices['ck'],
            'categories': card.categories[0],
            'quantity': card.quantity
        }
    for card in (deck.cards) ])
    if save_path is not None:
        logger.debug(f"Salvando {deck.name}.csv em {save_path}")
        deck_cards.to_csv(f"{save_path}/{deck.name}.csv", index=False)
    return deck_cards

def main_recs_commander(edhrec_handler, commander, synergy_threshold=0.20):
    high_synergy_cards = edhrec_handler.get_commander_cards(commander)
    dataframe_recs = pd.DataFrame()
    for key in high_synergy_cards.keys():
        dataframe_recs = pd.concat([dataframe_recs, pd.DataFrame(high_synergy_cards[key]).assign(category=key)])

    df_recs = dataframe_recs[dataframe_recs['synergy'] > synergy_threshold]

    card_details = pd.DataFrame.from_dict(df_recs.apply(lambda x: edhrec_handler.get_card_details(x['name']), axis=1, result_type='expand'))
    return card_details

def scrython_search(query):
    card =scrython.cards.Search(q=f'o:"~ {query}"')
    card_data = pd.DataFrame(card.data())
    return card_data[['name', 'mana_cost', 'cmc', 'prices', 'keywords', 'all_parts']]

edhrec = EDHRec()
