from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import time
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from urllib.parse import quote
from io import StringIO
from loguru import logger
app = FastAPI(title="MTG Commander Helper API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def fetch_scryfall(url: str) -> Dict:
    """Fetch data from Scryfall API using aiohttp"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 404:
                return {}
            data = await response.json()
            await asyncio.sleep(0.1)  # Rate limiting
            return data

@app.get("/api/cards/search/{lang}/{card_name}/{page}")
async def search_card_endpoint(lang: str = "en", card_name: str = "Sol Ring", page: int = 1):
    """
    Endpoint para buscar uma carta por nome
    """
    try:
        logger.debug(f"Searching for card: {card_name}")
        # Search by name first
        url = f"https://api.scryfall.com/cards/search?q=o:\"{quote(card_name)}\"&page={page}"
        data = await fetch_scryfall(url)
        if not data or not data.get('data'):
            raise HTTPException(status_code=404, detail="Card not found")
        logger.debug(f"{data['total_cards']} cartas encontradas")
        if lang != "en":
            return [await traduz_carta(card, lang) for card in data['data']]
        else:
            return data['data']
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

async def traduz_carta(data, lang: str) -> Dict:
    """
    Traduz uma carta para o idioma especificado, se disponível
    """
    if lang == 'en':
        return data  # Já está em inglês

    oracle_id = data['oracle_id']
    lang_url = f"https://api.scryfall.com/cards/search?q=oracle_id:{oracle_id}+lang:{lang}"
    
    translated_data = await fetch_scryfall(lang_url)
    if translated_data and translated_data.get('data'):
        return translated_data['data'][0]
    return data  # Retorna a carta original se não houver tradução



@app.get("/api/cards/set/{set_code}")
async def search_set_endpoint(set_code: str, lang: str = 'pt', page: int = 1):
    """
    Endpoint para buscar cartas de um set específico
    """
    try:
        url = f"https://api.scryfall.com/cards/search?q=set:{set_code}+lang:{lang}&page={page}"
        data = await fetch_scryfall(url)
        
        if not data or not data.get('data'):
            raise HTTPException(status_code=404, detail="No cards found for this set")

        return [traduz_carta(data, lang) for data in data['data']]
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cards/random")
async def random_card_endpoint(lang: str = 'pt'):
    """
    Endpoint para obter uma carta aleatória
    """
    try:
        # Get random card
        url = "https://api.scryfall.com/cards/random"
        data = await fetch_scryfall(url)
        if not data:
            raise HTTPException(status_code=404, detail="Could not get random card")
            
        # If language is not English, try to find the localized version
        if lang != 'en':
            oracle_id = data['oracle_id']
            lang_url = f"https://api.scryfall.com/cards/search?q=oracle_id:{oracle_id}+lang:{lang}"
            lang_data = await fetch_scryfall(lang_url)
            if lang_data and lang_data.get('data'):
                logger.debug(lang_data)
                return lang_data['data'][0]

        return data['data'][0]
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

def parse_deck_line(line: str) -> tuple[int, str]:
    """
    Parse a line from a deck list file.
    Supports multiple formats:
    - "1 Card Name"
    - "1x Card Name"
    - "1 Card Name (SET)"
    - "1x Card Name (SET) [category]"
    """
    try:
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Skip empty lines or comments
        if not line or line.startswith('//') or line.startswith('#'):
            return 0, ''
            
        # Handle set information
        if '(' in line:
            line = line.split('(')[0].strip()
        
        # Split quantity and name
        parts = line.split(None, 1)
        if len(parts) < 2:
            return 0, ''
            
        # Parse quantity (remove 'x' if present)
        quantity = parts[0].lower().rstrip('x')
        try:
            quantity = int(quantity)
        except ValueError:
            return 0, ''
            
        # Get card name
        name = parts[1].strip()
        if len(parts) < 4:
            return quantity, name, ''
        category = parts[3].lower().strip('x')
        return quantity, name, category
    except Exception:
        return 0, '', ''

@app.post("/api/deck/process")
async def process_deck_endpoint(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    lang: str = Form('pt')
):
    """
    Processa um deck a partir de um arquivo de texto ou texto direto.
    Retorna informações sobre todas as cartas do deck.
    """
    try:
        # Get deck list content
        if file:
            content = (await file.read()).decode()
        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="No deck list provided")
        
        # Process each line
        deck_cards = []
        for line in StringIO(content):
            quantity, card_name = parse_deck_line(line)
            if quantity > 0 and card_name:
                try:
                    logger.debug(f"Searching for card: {card_name}")
                    # Search by name first
                    url = f"https://api.scryfall.com/cards/search?q=!\"{quote(card_name)}\""
                    data = await fetch_scryfall(url)
                    if not data or not data.get('data'):
                        raise HTTPException(status_code=404, detail="Card not found")
                    logger.debug(f"{data['total_cards']} cartas encontradas")
                    if lang != "en":
                        card_data = await traduz_carta(data['data'][0], lang)
                    else:
                        card_data = data['data'][0]
                except aiohttp.ClientError as e:
                    raise HTTPException(status_code=500, detail=str(e))
                card_data['quantity'] = quantity
                deck_cards.append(card_data)
            
            # Rate limiting
            await asyncio.sleep(0.1)
    
        # Organize cards by type
        categorized_cards = {
            'commander': [],
            'lands': [],
            'creatures': [],
            'others': []
        }
        
        total_cards = 0
        for card in deck_cards:
            quantity = card.get('quantity', 1)
            total_cards += quantity
            
            # Check if it's a commander
            if 'oracle_text' in card and 'commander' in card['oracle_text'].lower():
                categorized_cards['commander'].append(card)
            # Check card type
            elif 'type_line' in card:
                type_line = card['type_line'].lower()
                if 'land' in type_line:
                    categorized_cards['lands'].append(card)
                elif 'creature' in type_line:
                    categorized_cards['creatures'].append(card)
                else:
                    categorized_cards['others'].append(card)
        
        # Calculate deck statistics
        stats = {
            'total_cards': total_cards,
            'unique_cards': len(deck_cards),
            'by_type': {
                'commander': len(categorized_cards['commander']),
                'lands': sum(c.get('quantity', 1) for c in categorized_cards['lands']),
                'creatures': sum(c.get('quantity', 1) for c in categorized_cards['creatures']),
                'others': sum(c.get('quantity', 1) for c in categorized_cards['others'])
            },
            'estimated_price': {
                'usd': sum(float(c.get('prices', {}).get('usd', 0) or 0) * c.get('quantity', 1) for c in deck_cards)
            }
        }
        
        return {
            'cards': categorized_cards,
            'statistics': stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def parse_deck_line(line: str) -> tuple[int, str]:
    """
    Parse a line from a deck list file.
    Supports multiple formats:
    - "1 Card Name"
    - "1x Card Name"
    - "1 Card Name (SET)"
    - "1x Card Name (SET)"
    """
    try:
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Skip empty lines or comments
        if not line or line.startswith('//') or line.startswith('#'):
            return 0, ''
            
        # Handle set information
        if '(' in line:
            line = line.split('(')[0].strip()
        
        # Split quantity and name
        parts = line.split(None, 1)
        if len(parts) < 2:
            return 0, ''
            
        # Parse quantity (remove 'x' if present)
        quantity = parts[0].lower().rstrip('x')
        try:
            quantity = int(quantity)
        except ValueError:
            return 0, ''
            
        # Get card name
        name = parts[1].strip()
        
        return quantity, name
    except Exception:
        return 0, ''

@app.post("/api/deck/process")
async def process_deck_endpoint(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    lang: str = Form('pt')
):
    """
    Processa um deck a partir de um arquivo de texto ou texto direto.
    Retorna informações sobre todas as cartas do deck.
    """
    try:
        # Get deck list content
        if file:
            content = (await file.read()).decode()
        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="No deck list provided")
        
        # Process each line
        deck_cards = []
        for line in StringIO(content):
            quantity, card_name, category = parse_deck_line(line)
            if quantity > 0 and card_name:
                # Search for card
                url = f"https://api.scryfall.com/cards/search?q=!\"{quote(card_name)}\""
                data = await fetch_scryfall(url)
                
                if data and data.get('data'):
                    card_data = data['data'][0]
                    oracle_id = card_data['oracle_id']
                    
                    # If language is not English, try to find the localized version
                    if lang != 'en':
                        lang_url = f"https://api.scryfall.com/cards/search?q=oracle_id:{oracle_id}+lang:{lang}"
                        lang_data = await fetch_scryfall(lang_url)
                        
                        if lang_data and lang_data.get('data'):
                            card_data = lang_data['data'][0]
                    
                    # Add quantity to card data
                    card_data['quantity'] = quantity
                    card_data['category'] = category
                    deck_cards.append(card_data)
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        # Organize cards by type
        categorized_cards = {
            'commander': [],
            'lands': [],
            'creatures': [],
            'others': []
        }
        
        total_cards = 0
        for card in deck_cards:
            quantity = card.get('quantity', 1)
            total_cards += quantity
            
            # Check if it's a commander
            if card.get('category') == 'commander':
                categorized_cards['commander'].append(card)
            # Check card type
            elif 'type_line' in card:
                type_line = card['type_line'].lower()
                if 'land' in type_line:
                    categorized_cards['lands'].append(card)
                elif 'creature' in type_line:
                    categorized_cards['creatures'].append(card)
                else:
                    categorized_cards['others'].append(card)
        
        # Calculate deck statistics
        stats = {
            'total_cards': total_cards,
            'unique_cards': len(deck_cards),
            'by_type': {
                'commander': len(categorized_cards['commander']),
                'lands': sum(c.get('quantity', 1) for c in categorized_cards['lands']),
                'creatures': sum(c.get('quantity', 1) for c in categorized_cards['creatures']),
                'others': sum(c.get('quantity', 1) for c in categorized_cards['others'])
            },
            'estimated_price': {
                'usd': sum(
                    (float(c.get('prices', {}).get('usd', 0) or 0) * c.get('quantity', 1)
                    for c in deck_cards)
                )
            }
        }
        return {
            'cards': categorized_cards,
            'statistics': stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
