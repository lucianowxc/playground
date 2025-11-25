import requests
from bs4 import BeautifulSoup
import time
import re
import requests
from bs4 import BeautifulSoup
from pyedhrec import EDHRec  # Ajuste o nome do módulo conforme necessário
import random
import pandas as pd
from loguru import logger
from tqdm import tqdm

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
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://edhrec.com"
        self.current_build_id = None
        self._get_build_id()
    
    def _get_build_id(self):
        """Obtém o build ID atual do EDHRec"""
        try:
            response = self.session.get(self.base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.get('src') and '_buildManifest.js' in script.get('src'):
                    build_id = script.get('src').split('/')[2]
                    self.current_build_id = build_id
                    logger.info(f"Build ID obtido: {build_id}")
                    break
        except Exception as e:
            logger.error(f"Erro ao obter build ID: {e}")
    
    def format_card_name(self, card_name: str) -> str:
        """Formata o nome da carta para URL"""
        return card_name.lower().replace(' ', '-').replace(',', '')
    
    def get_commander_data(self, card_name: str) -> dict:
        """Obtém dados do comandante via API JSON do Next.js"""
        formatted_name = self.format_card_name(card_name)
        
        if not self.current_build_id:
            self._get_build_id()
            
        url = f"{self.base_url}/_next/data/{self.current_build_id}/commanders/{formatted_name}.json"
        headers = {"User-Agent": get_random_ua()}
        
        try:
            logger.info(f"Buscando dados para: {card_name}")
            logger.info(f"URL: {url}")
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Dados obtidos com sucesso para {card_name}")
                return data
            else:
                logger.warning(f"Status code {response.status_code} para {card_name}")
                # Fallback: tentar via scraping tradicional
                return self._get_commander_data_fallback(card_name)
                
        except Exception as e:
            logger.error(f"Erro ao obter dados do comandante {card_name}: {e}")
            return self._get_commander_data_fallback(card_name)
    
    def _get_commander_data_fallback(self, card_name: str) -> dict:
        """Fallback: obtém dados via scraping HTML tradicional"""
        formatted_name = self.format_card_name(card_name)
        url = f"{self.base_url}/commanders/{formatted_name}"
        headers = {"User-Agent": get_random_ua()}
        
        try:
            logger.info(f"Tentando fallback para: {card_name} na URL {url}")
            response = self.session.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair dados básicos da página
            data = {
                'name': card_name,
                'url': url,
                'soup': soup,
                'fallback': True
            }
            return data
            
        except Exception as e:
            logger.error(f"Erro no fallback para {card_name}: {e}")
            return {}
    
    def get_recommendations(self, deck_data):
        """Extrai recomendações dos dados do deck - VERSÃO CORRIGIDA"""
        try:
            logger.info("Iniciando extração de recomendações...")
            
            # Verificar se é dados JSON (Next.js) ou fallback (HTML)
            if 'pageProps' in deck_data:
                # Dados JSON do Next.js
                return self._extract_recommendations_from_json(deck_data)
            elif 'soup' in deck_data:
                # Dados HTML do fallback
                return self._extract_recommendations_from_html(deck_data)
            else:
                logger.error("Formato de dados não reconhecido")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Erro ao extrair recomendações: {e}")
            return pd.DataFrame()
    
    def _extract_recommendations_from_json(self, deck_data):
        """Extrai recomendações dos dados JSON do Next.js"""
        try:
            page_props = deck_data.get('pageProps', {})
            container = page_props.get('container', {})
            json_dict = container.get('json_dict', {})
            cardlists = json_dict.get('cardlists', [])
            
            logger.info(f"Encontradas {len(cardlists)} listas de cartas")
            
            recommendations = []
            
            for cardlist in cardlists:
                header = cardlist.get('header', 'Unknown')
                cardviews = cardlist.get('cardviews', [])
                
                logger.info(f"Processando lista: {header} com {len(cardviews)} cartas")
                
                for cardview in cardviews:
                    if isinstance(cardview, dict):
                        card_name = cardview.get('name', '')
                        if card_name:
                            recommendations.append({
                                'name': card_name,
                                'category': header,
                                'salt': cardview.get('salt', 0),
                                'score': cardview.get('score', 0)
                            })
            
            df = pd.DataFrame(recommendations)
            logger.info(f"Extraídas {len(df)} recomendações totais")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao extrair do JSON: {e}")
            return pd.DataFrame()
    
    def _extract_recommendations_from_html(self, deck_data):
        """Extrai recomendações do HTML (fallback)"""
        try:
            soup = deck_data.get('soup')
                
            cardList = soup.find_all('div', class_=re.compile('.*Grid_cardlist.*'))

            all_returns = []
            for category in cardList:
                category_name = category.get('id')
                
                flexContent = category.find_all('div', class_=re.compile('.*d-flex justify-content-center mb-2*'))

                for content in flexContent:
                    card_name = content.find_all('span', class_=re.compile('.*Card_name__*'))[0].get_text()
                    card_synergy = int(content.find_all('a', class_=re.compile('.*CardLabel_line*'))[0].get_text().split("%")[0])/100
                    result = {
                        'name': card_name,
                        'score': card_synergy,
                        'category': category_name,
                        'salt': 0
                    }
                    all_returns.append(result)
                logger.debug(f"Recomendações: {len(all_returns)} cartas processadas.")
            return pd.DataFrame(all_returns)
        
        except Exception as e:
            logger.error(f"Erro ao extrair do HTML: {e}")
            return pd.DataFrame()
            
            
    
    def get_card_prices(self, card_names, max_price=None):
        """Obtém preços reais das cartas usando Scryfall API"""
        prices = []
        
        for card_name in tqdm(card_names, desc="Buscando preços"):
            try:
                # Usar Scryfall API para preços reais
                scryfall_url = f"https://api.scryfall.com/cards/named"
                params = {'exact': card_name}
                
                response = self.session.get(scryfall_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    card_data = response.json()
                    
                    # Tentar obter preço em USD
                    usd_price = None
                    price_data = card_data.get('prices', {})
                    
                    # Prioridade: usd > usd_foil > usd_etched
                    if price_data.get('usd'):
                        usd_price = float(price_data['usd'])
                    elif price_data.get('usd_foil'):
                        usd_price = float(price_data['usd_foil'])
                    elif price_data.get('usd_etched'):
                        usd_price = float(price_data['usd_etched'])
                    
                    if usd_price is not None:
                        # Aplicar filtro de preço se especificado
                        if max_price is None or usd_price <= max_price:
                            price_range = 'budget' if usd_price <= 2.0 else 'mid' if usd_price <= 10.0 else 'premium'
                            
                            prices.append({
                                'name': card_name,
                                'price': usd_price,
                                'price_range': price_range,
                                'cmc': card_data.get('cmc', 0),
                                'type_line': card_data.get('type_line', ''),
                                'color_identity': card_data.get('color_identity', [])
                            })
                    else:
                        logger.debug(f"Preço não encontrado para: {card_name}")
                else:
                    logger.debug(f"Carta não encontrada no Scryfall: {card_name}")
                
                # Rate limiting respeitoso
                time.sleep(0.05)
                
            except Exception as e:
                logger.debug(f"Erro ao buscar preço para {card_name}: {e}")
                continue
        
        return pd.DataFrame(prices)
