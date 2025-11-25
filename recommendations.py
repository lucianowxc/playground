from edhrec_extended import EDHRecExtended
from deck_analyzer import DeckAnalyzer
from loguru import logger
from deck_recommendation import DeckRecommendationSystem
from tqdm.notebook import tqdm
from pathlib import Path
import pandas as pd
import argparse
# Inicializar o sistema
recommender = DeckRecommendationSystem()

def process_commander_deck_list(file):
    deck_df = pd.read_csv(file)
    deck_list = deck_df['name'].tolist()
    commander = deck_df[deck_df['categories'] == 'Commander'].values[0][1]
    return (commander, deck_list)

def main(*args, **kwargs):
    parser = argparse.ArgumentParser(description="Sistema de Recomendação de Decks MTG")
    parser.add_argument('-d', '--deck_file', type=str, required=True, help='Caminho para o arquivo CSV do deck')
    parser.add_argument('-b', '--budget', type=float, default=5.0, help='Orçamento máximo por carta')
    parser.add_argument('-t', '--top_n', type=int, default=20, help='Número de recomendações a retornar')
    
    parsed_args = parser.parse_args(*args, **kwargs)
    
    deck_file = parsed_args.deck_file
    budget = parsed_args.budget
    top_n = parsed_args.top_n
    
    # Carregar dados de análise (uma vez só)
    print("Carregando dados de análise...")
    recommender.load_analyzer_data()
    
    (commander, deck_list) = process_commander_deck_list(deck_file)
    print(commander)
    print(deck_list)
        
    # Obter recomendações
    print(f"\nObtendo recomendações para {commander}...")
    recommendations = recommender.get_detailed_recommendations(
        deck_list=deck_list,
        commander=commander,
        budget=budget,
        top_n=top_n
    )
    
    if not recommendations.empty:
        print(f"\n=== RECOMENDAÇÕES PARA {commander.upper()} (ATÉ ${budget}) ===")
        print(f"{'#':2} {'Carta':35} {'Preço':6} {'Sinergia':8} {'Categoria'}")
        print("-" * 70)
        for i, (_, row) in enumerate(recommendations.iterrows(), 1):
            print(f"{i:2}. {row['name']:35} ${row['price']:5.2f} {row['synergy_percent']:8} {row.get('category', 'N/A')}")
    else:
        print("Nenhuma recomendação encontrada.")
    recommendations.to_csv(f'{Path(deck_file).stem}_recommendations.csv', index=False)

if __name__ == "__main__":
    import sys
    main(args=sys.argv[1:])