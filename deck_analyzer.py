from loguru import logger
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
from tqdm import tqdm
import os

class DeckAnalyzer:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.decks_data = []
        self.deck_vectors = []
        self.card_names = []
        self.card_to_index = {}
        self.index_to_card = {}
        self.tfidf_matrix = None
        self.card_frequencies = None
        
    def load_decks_from_csv(self, csv_file=None):
        """Carrega decks de arquivos CSV"""
        logger.info("Carregando decks de CSVs...")
        
        if csv_file and os.path.isfile(csv_file):
            self._load_single_csv(csv_file)
        else:
            self._load_multiple_csvs()
    
    def _load_single_csv(self, csv_file):
        """Carrega de um único arquivo CSV contendo múltiplos decks"""
        try:
            df = pd.read_csv(csv_file)
            
            for deck_name, group in df.groupby('deck_name'):
                cards = group['name'].tolist()
                if len(cards) >= 10:
                    self.decks_data.append({
                        'name': deck_name,
                        'cards': cards,
                        'card_count': len(cards)
                    })
                    self.deck_vectors.append(cards)
                    
            logger.info(f"Carregados {len(self.decks_data)} decks do arquivo {csv_file}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar CSV: {e}")
    
    def _load_multiple_csvs(self):
        """Carrega de múltiplos arquivos CSV no diretório data"""
        import os
        csv_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
        
        if not csv_files:
            logger.warning("Nenhum arquivo CSV encontrado no diretório")
            return
        
        for csv_file in tqdm(csv_files, desc="Processando CSVs"):
            try:
                filepath = os.path.join(self.data_dir, csv_file)
                df = pd.read_csv(filepath)
                
                if not df.empty:
                    deck_name = df['deck_name'].iloc[0] if 'deck_name' in df.columns else csv_file.replace('.csv', '')
                    cards = df['name'].tolist()
                    
                    if len(cards) >= 10:
                        self.decks_data.append({
                            'name': deck_name,
                            'cards': cards,
                            'card_count': len(cards),
                            'file': csv_file
                        })
                        self.deck_vectors.append(cards)
                        
            except Exception as e:
                logger.debug(f"Erro ao processar {csv_file}: {e}")
                continue
        
        logger.info(f"Carregados {len(self.decks_data)} decks de {len(csv_files)} arquivos CSV")
    
    def build_custom_tfidf(self):
        """Constrói uma matriz TF-IDF customizada onde cada carta é um token único"""
        logger.info("Construindo matriz TF-IDF customizada...")
        
        if not self.deck_vectors:
            logger.error("Nenhum deck foi carregado!")
            return
        
        # Coleta todas as cartas únicas
        all_cards = set()
        for deck in self.deck_vectors:
            all_cards.update(deck)
        
        self.card_names = sorted(list(all_cards))
        self.card_to_index = {card: idx for idx, card in enumerate(self.card_names)}
        self.index_to_card = {idx: card for idx, card in enumerate(self.card_names)}
        
        # Calcula document frequency (DF)
        doc_freq = np.zeros(len(self.card_names))
        for deck in self.deck_vectors:
            unique_cards_in_deck = set(deck)
            for card in unique_cards_in_deck:
                if card in self.card_to_index:
                    doc_freq[self.card_to_index[card]] += 1
        
        # Calcula IDF
        total_decks = len(self.deck_vectors)
        idf = np.log(total_decks / (doc_freq + 1))
        
        # Constrói matriz TF-IDF
        self.tfidf_matrix = np.zeros((total_decks, len(self.card_names)))
        
        for deck_idx, deck in enumerate(self.deck_vectors):
            card_counts = Counter(deck)
            total_cards_in_deck = len(deck)
            
            for card, count in card_counts.items():
                if card in self.card_to_index:
                    card_idx = self.card_to_index[card]
                    tf = count / total_cards_in_deck
                    self.tfidf_matrix[deck_idx, card_idx] = tf * idf[card_idx]
        
        self.card_frequencies = doc_freq
        
        logger.info(f"Matriz TF-IDF construída: {self.tfidf_matrix.shape}")
        logger.info(f"Total de decks: {len(self.deck_vectors)}")
        logger.info(f"Total de cartas únicas: {len(self.card_names)}")
    
    def calculate_deck_synergy_score(self, card_name, deck_list):
        """Calcula score de sinergia entre uma carta e um deck"""
        if card_name not in self.card_to_index:
            return 0.0
        
        card_idx = self.card_to_index[card_name]
        
        # Encontra decks similares ao deck atual
        deck_vector = self._create_deck_vector(deck_list)
        if deck_vector is None:
            return 0.0
        
        # Calcula similaridade entre a carta e o deck
        card_vector = self.tfidf_matrix.T[card_idx]
        similarity = cosine_similarity([card_vector], [deck_vector])[0][0]
        
        return similarity
    
    def _create_deck_vector(self, deck_list):
        """Cria um vetor representando o deck"""
        if not deck_list or self.tfidf_matrix is None:
            return None
        
        # Encontra índices das cartas no deck
        deck_indices = []
        for card in deck_list:
            if card in self.card_to_index:
                deck_indices.append(self.card_to_index[card])
        
        if not deck_indices:
            return None
        
        # Cria vetor médio do deck
        deck_vectors = self.tfidf_matrix.T[deck_indices]
        deck_vector = np.mean(deck_vectors, axis=0)
        
        return deck_vector
    
    def find_card_associations(self, card_name, top_n=15):
        """Encontra associações baseadas em co-ocorrência"""
        if card_name not in self.card_to_index:
            matches = [card for card in self.card_names if card_name.lower() in card.lower()]
            if matches:
                card_name = matches[0]
            else:
                return []
        
        card_idx = self.card_to_index[card_name]
        
        # Encontra decks que contêm a carta alvo
        decks_with_card = []
        for deck_idx, deck in enumerate(self.deck_vectors):
            if card_name in deck:
                decks_with_card.append(deck_idx)
        
        if len(decks_with_card) == 0:
            return []
        
        # Calcula frequência de outras cartas nesses decks
        card_counter = Counter()
        for deck_idx in decks_with_card:
            deck_cards = set(self.deck_vectors[deck_idx])
            for card in deck_cards:
                if card != card_name:
                    card_counter[card] += 1
        
        total_decks_with_card = len(decks_with_card)
        results = []
        
        for card, count in card_counter.most_common(top_n):
            probability = count / total_decks_with_card
            card_freq = self.card_frequencies[self.card_to_index[card]] if card in self.card_to_index else 0
            expected_prob = card_freq / len(self.deck_vectors) if len(self.deck_vectors) > 0 else 0
            lift = probability / expected_prob if expected_prob > 0 else 0
            
            results.append({
                'card': card,
                'probability': probability,
                'probability_percent': f"{probability * 100:.1f}%",
                'co_occurrence_count': count,
                'total_decks_with_target': total_decks_with_card,
                'lift': lift
            })
        
        results.sort(key=lambda x: x['lift'], reverse=True)
        return results[:top_n]
