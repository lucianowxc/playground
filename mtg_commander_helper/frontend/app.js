const API_URL = 'http://localhost:8000/api';
let pagination = 1; // Default to first page; can be modified to take user input for page number

function previousPage() {
    if (pagination > 1) {
        pagination--;
        document.getElementById('currentPage').innerText = "Página " + pagination;
        searchCard();
    }
}

function nextPage() {
    pagination++;
    document.getElementById('currentPage').innerText = "Página " + pagination;
    searchCard();
}

// Card Search and Display Functions
async function searchCard() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();
    if (!searchTerm) {
        alert('Por favor, digite um termo de busca.');
        return;
    }
    
    displayLoading('Buscando carta...');
    
    try {
        const response = await fetch(`${API_URL}/cards/search/en/${encodeURIComponent(searchTerm)}/${pagination}`);
        const data = await response.json();
        // if (data && data.length > 0) {
        //     if (data.length < 60) {
        //         // No more pages
        //         document.getElementById('nextPage').style.display = 'none';
        //         return;
        //     }
        //     if (pagination === 1) {
        //         // No more pages
        //         document.getElementById('previousPage').style.display = 'none';
        //         return;
        //     }
        //     document.getElementById('currentPage').innerText = pagination;
        //     document.getElementById('paginationControls').style.display = 'flex';
        // } else {
        //     document.getElementById('paginationControls').style.display = 'none';
        // }
        if (!response.ok) {
            throw new Error(data.detail || 'Erro ao buscar cartas');
        }
        
        displayCards(Array.isArray(data) ? data : [data]);
    } catch (error) {
        displayError(error.message);
    }
}

async function getRandomCard() {
    displayLoading('Buscando carta aleatória...');
    
    try {
        const response = await fetch(`${API_URL}/cards/random`);
        const card = await response.json();
        
        if (!response.ok) {
            throw new Error(card.detail || 'Erro ao buscar carta aleatória');
        }
        
        displayCards([card]);
    } catch (error) {
        displayError(error.message);
    }
}

// Deck Processing Functions
async function uploadDeckFile() {
    const fileInput = document.getElementById('deckFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Por favor, selecione um arquivo.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/deck/process`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Erro ao processar deck');
        }
        
        displayDeck(data);
    } catch (error) {
        displayError(`Erro ao enviar arquivo: ${error.message}`);
    }
}

async function processDeckText() {
    const textArea = document.getElementById('deckText');
    const text = textArea.value.trim();
    
    if (!text) {
        alert('Por favor, insira a lista do deck.');
        return;
    }

    const formData = new FormData();
    formData.append('text', text);
    
    try {
        const response = await fetch(`${API_URL}/deck/process`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Erro ao processar deck');
        }
        
        displayDeck(data);
    } catch (error) {
        displayError(`Erro ao processar deck: ${error.message}`);
    }
}

// Display Helper Functions
function displayLoading(message) {
    const cardContainer = document.getElementById('cardContainer');
    cardContainer.innerHTML = `<p>${message}</p>`;
}

function displayError(message) {
    const cardContainer = document.getElementById('cardContainer');
    cardContainer.innerHTML = `
        <div class="error">
            ${message}
        </div>
    `;
}

function createCardHtml(cardData) {
    const imageUrl = cardData.image_uris?.normal || cardData.card_faces?.[0]?.image_uris?.normal;
    const name = cardData.printed_name || cardData.name;
    const typeLine = cardData.printed_type_line || cardData.type_line;
    const text = cardData.printed_text || cardData.oracle_text;
    const quantity = cardData.quantity || 1;
    const price = cardData.prices?.usd ? `$${cardData.prices.usd}` : 'Preço não disponível';
    const ligamagic_url = `https://www.ligamagic.com.br/?view=cards/card&card=${encodeURIComponent(cardData.name)}`;
    return `
        <div class="card">
            ${imageUrl ? `<img src="${imageUrl}" alt="${name}" class="card-image" loading="lazy">` : ''}
            <div class="card-info">
                <div class="card-name"><a href="${ligamagic_url}" >${quantity > 1 ? `${quantity}x ` : ''}${name}</a></div>
                <div class="card-type">${typeLine}</div>
                ${text ? `<div class="card-text">${text}</div>` : ''}
                <div class="card-price">${price}</div>
            </div>
        </div>
    `;
}

function displayCards(cards) {
    const cardContainer = document.getElementById('cardContainer');
    
    if (!cards || cards.length === 0) {
        displayError('Nenhuma carta encontrada.');
        return;
    }
    
    cardContainer.innerHTML = '';
    cards.forEach(card => {
        cardContainer.innerHTML += createCardHtml(card);
    });
}

function displayDeck(deckData) {
    const cardContainer = document.getElementById('cardContainer');
    const { cards, statistics } = deckData;
    
    // Display statistics
    const statsHtml = `
        <div class="deck-stats">
            <h3>Estatísticas do Deck</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${statistics.total_cards}</div>
                    <div class="stat-label">Total de Cartas</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${statistics.by_type.lands}</div>
                    <div class="stat-label">Terrenos</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${statistics.by_type.creatures}</div>
                    <div class="stat-label">Criaturas</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${statistics.by_type.others}</div>
                    <div class="stat-label">Outras Magias</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">$${statistics.estimated_price.usd.toFixed(2)}</div>
                    <div class="stat-label">Preço Estimado</div>
                </div>
            </div>
        </div>
    `;
    
    cardContainer.innerHTML = statsHtml;
    
    // Display each section
    const sections = [
        { key: 'commander', title: 'Commander' },
        { key: 'creatures', title: 'Criaturas' },
        { key: 'lands', title: 'Terrenos' },
        { key: 'others', title: 'Outras Magias' }
    ];
    
    for (const section of sections) {
        if (cards[section.key] && cards[section.key].length > 0) {
            const sectionHtml = `
                <div class="deck-section">
                    <h3>${section.title}</h3>
                    <div class="card-container">
                        ${cards[section.key].map(card => createCardHtml(card)).join('')}
                    </div>
                </div>
            `;
            cardContainer.innerHTML += sectionHtml;
        }
    }
}

// Event Listeners
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchCard();
    }
});