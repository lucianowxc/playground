from edhrec_extended import EDHRecExtended
from deck_analyzer import DeckAnalyzer
from loguru import logger
import pandas as pd

class DeckRecommendationSystem:
    def __init__(self, data_dir='data'):
        self.analyzer = DeckAnalyzer(data_dir)
        self.edhrec = EDHRecExtended()
        
    def load_analyzer_data(self):
        """Carrega e prepara os dados do analisador"""
        self.analyzer.load_decks_from_csv()
        self.analyzer.build_custom_tfidf()
        
    def get_budget_recommendations(self, deck_list, commander, budget=10.0, top_n=20):
        """
        Obtém recomendações dentro do orçamento com base na sinergia
        
        Args:
            deck_list: Lista de cartas no deck atual
            commander: Nome do comandante
            budget: Orçamento máximo por carta
            top_n: Número de recomendações a retornar
        """
        logger.info(f"Buscando recomendações para {commander} com orçamento ${budget}")
        
        # 1. Obter recomendações do EDHRec
        commander_data = self.edhrec.get_commander_data(commander)
        logger.debug(f"Commander data: {commander_data}")
        recommendations_df = self.edhrec.get_recommendations(commander_data)
        logger.debug(f"Recommendations: {recommendations_df}")
        if recommendations_df.empty:
            logger.warning("Nenhuma recomendação encontrada no EDHRec")
            return pd.DataFrame()
        
        # 2. Obter preços e filtrar por orçamento
        card_names = recommendations_df['name'].tolist()
        
        prices_df = self.edhrec.get_card_prices(card_names, max_price=budget)
        
        if prices_df.empty:
            logger.warning("Nenhuma carta dentro do orçamento encontrada")
            return pd.DataFrame()
        
        # 3. Combinar recomendações com preços
        recommendations_with_prices = recommendations_df.merge(
            prices_df, on='name', how='inner'
        )
        
        # 4. Remover cartas que já estão no deck
        existing_cards = set(deck_list)
        recommendations_filtered = recommendations_with_prices[
            ~recommendations_with_prices['name'].isin(existing_cards)
        ]
        
        if recommendations_filtered.empty:
            logger.info("Todas as recomendações já estão no deck")
            return pd.DataFrame()
        
        # 5. Calcular scores de sinergia
        synergy_scores = []
        for _, row in recommendations_filtered.iterrows():
            card_name = row['name']
            score = self.analyzer.calculate_deck_synergy_score(card_name, deck_list)
            synergy_scores.append(score)
        
        recommendations_filtered['synergy_score'] = synergy_scores
        recommendations_filtered['synergy_percent'] = recommendations_filtered['synergy_score'].apply(
            lambda x: f"{x*100:.1f}%"
        )
        
        # 6. Ordenar por sinergia e preço
        recommendations_sorted = recommendations_filtered.sort_values(
            ['synergy_score', 'price'], 
            ascending=[False, True]
        ).head(top_n)
        
        return recommendations_sorted
    
    def get_detailed_recommendations(self, deck_list, commander, budget=10.0, top_n=20):
        """
        Retorna recomendações detalhadas com análise de sinergia
        """
        recommendations = self.get_budget_recommendations(deck_list, commander, budget)
        
        if recommendations.empty:
            return recommendations
        
        # Adicionar análise de associação para as top recomendações
        detailed_results = []
        for _, row in recommendations.iterrows():
            card_name = row['name']
            
            # Análise de associação com o comandante
            commander_associations = self.analyzer.find_card_associations(commander, top_n=top_n)
            card_associations = self.analyzer.find_card_associations(card_name, top_n=top_n)
            
            # Encontrar associações em comum
            commander_cards = {assoc['card'] for assoc in commander_associations}
            card_cards = {assoc['card'] for assoc in card_associations}
            common_associations = commander_cards.intersection(card_cards)
            
            detailed_results.append({
                'name': card_name,
                'price': row['price'],
                'price_range': row['price_range'],
                'synergy_score': row['synergy_score'],
                'synergy_percent': row['synergy_percent'],
                'common_synergies': list(common_associations)[:3],
                'synergy_count': len(common_associations)
            })
        
        return pd.DataFrame(detailed_results)
