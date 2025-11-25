import requests
from bs4 import BeautifulSoup
import time
import re
import requests
from bs4 import BeautifulSoup
from pyedhrec import EDHRec  # Ajuste o nome do módulo conforme necessário
import random
import pandas as pd

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.3',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Safari/605.1.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3'
]


def get_random_ua() -> str:
    return random.choice(user_agents)

class EDHRecExtended(EDHRec):
    """
    Extensão da classe EDHRec para incluir funcionalidades de arquétipos de deck (themes).
    """

    def _build_nextjs_uri_theme(self, card_name: str, theme: str) -> tuple:
        """
        Constrói a URI para um deck específico de um comandante baseado em tema (archetype).
        Ex: /commanders/ms-bumbleflower/group-hug
        """
        self.check_build_id()
        formatted_card_name = self.format_card_name(card_name)
        uri = f"{self.base_url}/_next/data/{self.current_build_id}/commanders/{formatted_card_name}/{theme}.json"
        query_params = {
            "commanderName": formatted_card_name,
            "themeName": theme
        }
        return uri, query_params

    def get_commander_theme_data(self, card_name: str, theme: str) -> dict:
        """
        Obtém os dados de um deck específico baseado em tema (archetype).
        """
        uri, query_params = self._build_nextjs_uri_theme(card_name, theme)
        res = self._get(uri, query_params=query_params)
        data = self._get_nextjs_data(res)
        return data

    def get_commander_themes(self, card_name: str) -> list:
        """
        Obtém a lista de temas (archetypes) disponíveis para um comandante.
        Primeiro tenta obter via API, se não funcionar, faz scraping.
        """
        # A página de comandante principal pode ter os temas listados
        commander_data = self.get_commander_data(card_name)
        # Isso depende da estrutura real dos dados
        # Vamos tentar extrair de "container" ou "json_dict"
        container = commander_data.get("container", {})
        json_dict = container.get("json_dict", {})
        themes = json_dict.get("themes", [])  # Ajustar conforme a estrutura real
        # Se não estiver aqui, talvez seja necessário scraping
        if not themes:
            themes = self._scrape_commander_themes(card_name)
        return themes

    def _scrape_commander_themes(self, card_name: str) -> list:
        """
        Método auxiliar para scraping dos temas (archetypes) de um comandante.
        """
        formatted_card_name = self.format_card_name(card_name)
        url = f"{self.base_url}/commanders/{formatted_card_name}"
        headers = {
            "User-Agent": get_random_ua()
        }
        response = self.session.get(url, headers=headers)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        # Exemplo: encontrar links ou botões que apontem para temas
        # Isso precisa ser ajustado com base na estrutura real do HTML
        # Procurando por links que terminem com /{comandante}/{tema}
        theme_links = soup.find_all('a', href=re.compile(rf'/commanders/{formatted_card_name}/[\w-]+$'))
        themes = []
        for link in theme_links:
            href = link.get('href')
            theme = href.split('/')[-1]
            if theme not in themes:
                themes.append(theme)
        return themes

    # Sua função adaptada para ser um método da classe
    def get_recommendations(self, deck_data):
        df_cards_all = pd.DataFrame()
        for i, category in enumerate(deck_data['container']['json_dict']['cardlists']):
            df_cards_category = pd.DataFrame(
                pd.DataFrame(deck_data['container']['json_dict']['cardlists']).iloc[i]['cardviews']
            ).assign(category=category['header'])
            df_cards_all = pd.concat([df_cards_all, df_cards_category])
        return df_cards_all
    
    def get_commander_theme_data_with_prices(self, card_name: str, theme: str, max_price: float = None) -> pd.DataFrame:
        """
        Extrai as cartas do deck_data, incluindo categoria e preço (se disponível).
        """
        
        # 1. Obter dados do deck de arquétipo
        deck_data = self.get_commander_theme_data(card_name, theme)

        # 2. Extrair cartas com categorias (sua função original adaptada)
        df_cartas = self.get_recommendations(deck_data)

        # 3. Obter detalhes das cartas (preço, tipo, etc) via get_card_list
        nomes_cartas = df_cartas['name'].tolist()
        detalhes = self.get_card_list(nomes_cartas)['cards']
        
        # 4. Converter detalhes para DataFrame e extrair preço
        detalhes_list = []
        for card in detalhes.values():
            card_detail = card.get('name', {})
            
            price = (
                card.get('prices', {}).get('tcgplayer', {}).get('price')
                if card.get('prices') and 'tcgplayer' in card.get('prices', {})
                else None
            )
            detalhes_list.append({
                'name': card_detail,
                'price': price,
                'cmc': card.get('cmc'),
                'salt': card.get('salt'),
                'primary_type': card.get('primary_type'),
                'subtypes': card.get('subtypes'),
                'color_identity': card.get('color_identity'),
                'rarity': card.get('rarity')
            })

        df_detalhes = pd.DataFrame(detalhes_list)
        
        # 5. Combinar com df_cartas (usando 'left' para manter cartas sem preço também)
        df_final = df_cartas.merge(df_detalhes, on='name', how='left')

        # 6. Filtrar por preço, se especificado
        if max_price is not None:
            # Usar .notna() para garantir que só filtre onde o preço é válido
            df_final = df_final[df_final['price'].notna() & (df_final['price'] <= max_price)]

        return df_final
