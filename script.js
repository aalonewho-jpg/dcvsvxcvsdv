// Получение Telegram данных
let tg = window.Telegram?.WebApp || { initDataUnsafe: { user: { id: null } }, close: () => {} };
tg.expand?.();

let currentUser = null;
let currentPage = 'home';
let inventory = [];
let casesList = [
    { id: 'loser_check', name: 'Loser Check', price: 75, icon: 'LoserCheck.jpg' },
    { id: 'faceit_open', name: 'Faceit Open', price: 100, icon: 'FaceitOpen.jpg' },
    { id: 'alonewho_cs2', name: 'Alonewho CS2', price: 250, icon: 'AlonewhoCS2.jpg' },
    { id: 'free_leo', name: 'Free Leo', price: 120, icon: 'FreeLeo.jpg' },
    { id: 'delete_game', name: 'Delete Game', price: 80, icon: 'DeleteGame.jpg' },
    { id: 'b_rush', name: 'B Rush', price: 50, icon: 'BRush.jpg' },
    { id: 'a_rush', name: 'A Rush', price: 50, icon: 'ARush.jpg' },
    { id: 'sakura_event', name: 'Sakura Event', price: 400, icon: 'SakuraEvent.jpg' }
];

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    createSnowflakes();
    checkRegistration();
    
    document.getElementById('logoBtn')?.addEventListener('click', () => navigateTo('home'));
    document.getElementById('addCoinsBtn')?.addEventListener('click', openDepositModal);
    
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => navigateTo(item.dataset.page));
    });
});

// Снежинки
function createSnowflakes() {
    const container = document.getElementById('particles-container');
    for (let i = 0; i < 50; i++) {
        const flake = document.createElement('div');
        flake.className = 'snowflake';
        flake.innerHTML = '❄️';
        flake.style.left = Math.random() * 100 + '%';
        flake.style.animationDuration = 8 + Math.random() * 10 + 's';
        flake.style.animationDelay = Math.random() * 10 + 's';
        flake.style.fontSize = (4 + Math.random() * 6) + 'px';
        container.appendChild(flake);
    }
}

// Проверка регистрации
async function checkRegistration() {
    const telegramId = tg.initDataUnsafe?.user?.id;
    if (!telegramId) {
        document.getElementById('main-content').innerHTML = '<div class="register-card"><h1>❌</h1><p>Запустите приложение через Telegram бота</p></div>';
        return;
    }
    
    try {
        const res = await fetch(`/api/profile/${telegramId}`);
        if (res.ok) {
            currentUser = await res.json();
            currentUser.telegram_id = telegramId;
            await loadInventory();
            updateBalance();
            navigateTo('home');
        } else {
            showRegistrationForm(telegramId);
        }
    } catch(e) {
        showRegistrationForm(telegramId);
    }
}

function showRegistrationForm(telegramId) {
    document.getElementById('main-content').innerHTML = `
        <div class="register-card">
            <h1>РЕГИСТРАЦИЯ</h1>
            <div class="input-group">
                <div class="input-label">Nickname</div>
                <input type="text" id="regNick" class="input-field" placeholder="Введите ник (2-14 символов)">
            </div>
            <div class="input-group">
                <div class="input-label">ID</div>
                <input type="text" id="regGameId" class="input-field" placeholder="Ваш Faceit ID">
            </div>
            <button class="btn" id="registerBtn">Зарегистрироваться</button>
        </div>
    `;
    
    document.getElementById('registerBtn').addEventListener('click', async () => {
        const nickname = document.getElementById('regNick').value.trim();
        const gameId = document.getElementById('regGameId').value.trim();
        
        if (nickname.length < 2 || nickname.length > 14) {
            tg.showAlert?.('Ник должен быть от 2 до 14 символов') || alert('Ошибка');
            return;
        }
        if (gameId.length < 2 || gameId.length > 14) {
            tg.showAlert?.('ID должен быть от 2 до 14 символов') || alert('Ошибка');
            return;
        }
        
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: telegramId, nickname, game_id: gameId })
        });
        const data = await res.json();
        if (data.success) {
            tg.showAlert?.('Регистрация успешна!') || alert('Успех');
            checkRegistration();
        } else {
            tg.showAlert?.(data.error) || alert(data.error);
        }
    });
}

// Навигация
async function navigateTo(page) {
    currentPage = page;
    document.querySelectorAll('.nav-item').forEach((item, i) => {
        if (item.dataset.page === page) item.classList.add('active');
        else item.classList.remove('active');
    });
    
    const content = document.getElementById('main-content');
    if (!currentUser && page !== 'home') {
        content.innerHTML = '<div class="register-card"><p>Сначала зарегистрируйтесь</p></div>';
        return;
    }
    
    switch(page) {
        case 'home': await renderHome(); break;
        case 'inventory': await renderInventory(); break;
        case 'cases': await renderCases(); break;
        case 'faceit': content.innerHTML = '<div style="text-align:center;padding:50px"><h2>🚧</h2><p>В разработке</p></div>'; break;
        case 'profile': await renderProfile(); break;
    }
}

// Главная страница
async function renderHome() {
    const content = document.getElementById('main-content');
    content.innerHTML = `
        <div class="drops-container" id="recentDrops"></div>
        <div class="event-banner">
            <img src="event.png" style="max-width:100%;border-radius:20px" onerror="this.style.display='none'">
            <p>Временный ивент в честь открытия нашего проекта! Зарабатывайте очки славы и забирайте прикольные рамки, баннеры и темы, а также кейсы!</p>
        </div>
        <div class="glowing-text" style="text-align:center;font-size:28px;font-weight:800;margin:20px 0">
            «ЗАДАНИЕ = КЕЙС» ⭐
        </div>
        <div class="task-box" id="dailyTask">
            <span>📋 Просмотрите свой профиль</span>
            <button class="task-btn" id="startTaskBtn">начать</button>
        </div>
    `;
    
    // Симуляция выпадающих предметов
    const drops = [
        { name: 'ProGamer', item: 'Рамка "FACEIT"', icon: 'frame.png' },
        { name: 'S1mpleStyle', item: 'Баннер "Dragon"', icon: 'dragon.png' },
        { name: 'LeoKing', item: 'Тема "Космос"', icon: 'space.png' }
    ];
    const dropsContainer = document.getElementById('recentDrops');
    drops.forEach(drop => {
        dropsContainer.innerHTML += `
            <div class="drop-card">
                <div>👤 ${drop.name}</div>
                <div>🎁 ${drop.item}</div>
            </div>
        `;
    });
    
    // Проверка выполнено ли задание
    const taskDone = localStorage.getItem(`task_${currentUser.telegram_id}`);
    if (taskDone) {
        document.getElementById('dailyTask').innerHTML = '<span>✅ Задание выполнено!</span><span>Кейс в инвентаре</span>';
    } else {
        document.getElementById('startTaskBtn').addEventListener('click', async () => {
            await fetch('/api/complete_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ telegram_id: currentUser.telegram_id })
            });
            localStorage.setItem(`task_${currentUser.telegram_id}`, 'done');
            await loadInventory();
            tg.showAlert?.('✅ Задание выполнено! Кейс "Loser Check" добавлен в инвентарь!') || alert('Успех!');
            navigateTo('inventory');
        });
    }
}

// Инвентарь
async function renderInventory() {
    const content = document.getElementById('main-content');
    content.innerHTML = `<h2 class="section-title">ИНВЕНТАРЬ</h2><div class="inventory-grid" id="invGrid"></div>`;
    await loadInventory();
    const grid = document.getElementById('invGrid');
    
    if (inventory.length === 0) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center">Пусто</div>';
        return;
    }
    
    inventory.forEach(item => {
        const div = document.createElement('div');
        div.className = 'inv-item';
        div.innerHTML = `
            ${item.is_new ? '<div class="new-badge">NEW</div>' : ''}
            <img src="${item.icon}" style="width:60px;height:60px;object-fit:cover;border-radius:12px" onerror="this.src='https://via.placeholder.com/60'">
            <div style="margin-top:8px;font-size:12px">${item.name}</div>
        `;
        if (item.type === 'case') {
            div.addEventListener('click', () => openCase(item));
        }
        div.addEventListener('click', async () => {
            if (item.is_new) {
                await fetch('/api/mark_seen', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ telegram_id: currentUser.telegram_id, item_id: item.id })
                });
                item.is_new = false;
                div.querySelector('.new-badge')?.remove();
            }
        });
        grid.appendChild(div);
    });
}

// Открытие кейса с рулеткой
function openCase(caseItem) {
    const modal = document.createElement('div');
    modal.className = 'roulette-overlay';
    modal.innerHTML = `
        <div class="roulette-box">
            <h3>${caseItem.name}</h3>
            <img src="${caseItem.icon}" style="width:80px;margin:10px 0" onerror="this.src='https://via.placeholder.com/80'">
            <div class="roulette-items" id="rouletteSpin">
                <span>🎁 ???</span>
            </div>
            <button class="btn" id="spinBtn">Крутить!</button>
        </div>
    `;
    document.body.appendChild(modal);
    
    document.getElementById('spinBtn').addEventListener('click', async () => {
        const spinDiv = document.getElementById('rouletteSpin');
        spinDiv.innerHTML = '<span>🌀</span><span>🌀</span><span>🌀</span>';
        
        const res = await fetch('/api/open_case', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: currentUser.telegram_id, case_id: caseItem.id })
        });
        const data = await res.json();
        
        let counter = 0;
        const interval = setInterval(() => {
            const items = ['🎁', '✨', '⭐', '💎'];
            spinDiv.innerHTML = `<span>${items[Math.floor(Math.random()*items.length)]}</span><span>${items[Math.floor(Math.random()*items.length)]}</span><span>${items[Math.floor(Math.random()*items.length)]}</span>`;
            counter++;
            if (counter > 20) {
                clearInterval(interval);
                spinDiv.innerHTML = `<span>🎉 ${data.reward.name} 🎉</span>`;
                setTimeout(() => {
                    modal.remove();
                    loadInventory();
                    tg.showAlert?.(`Вы выиграли: ${data.reward.name}!`) || alert(`Поздравляем! ${data.reward.name}`);
                }, 1500);
            }
        }, 100);
    });
}

// Кейсы магазин
async function renderCases() {
    const content = document.getElementById('main-content');
    content.innerHTML = `<h2 class="section-title">КЕЙСЫ</h2><p style="text-align:center;color:#aaa">Открывайте кейсы, выбивайте прикольные плюхи!</p><div class="cases-grid" id="casesGrid"></div>`;
    
    const grid = document.getElementById('casesGrid');
    casesList.forEach(c => {
        const card = document.createElement('div');
        card.className = 'case-card';
        card.innerHTML = `
            <img src="${c.icon}" style="width:80px;height:80px;object-fit:cover;border-radius:16px" onerror="this.src='https://via.placeholder.com/80'">
            <div style="font-weight:700;margin:8px 0">${c.name}</div>
            <div class="case-price"><img src="coin.jpg" style="width:16px"> ${c.price}</div>
        `;
        card.addEventListener('click', () => buyCase(c));
        grid.appendChild(card);
    });
}

async function buyCase(caseData) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>${caseData.name}</h3>
            <p>Цена: ${caseData.price} <img src="coin.jpg" style="width:16px;display:inline"></p>
            <div class="modal-buttons">
                <button class="modal-btn cancel">Отмена</button>
                <button class="modal-btn confirm">Купить</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    modal.querySelector('.confirm').addEventListener('click', async () => {
        const res = await fetch('/api/buy_case', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: currentUser.telegram_id,
                case_name: caseData.name,
                case_price: caseData.price,
                case_icon: caseData.icon
            })
        });
        const data = await res.json();
        if (data.success) {
            tg.showAlert?.('Покупка успешна! Кейс в инвентаре.') || alert('Успех!');
            modal.remove();
            await loadInventory();
            updateBalance();
        } else {
            tg.showAlert?.('Не хватает монет!') || alert('Ошибка');
        }
    });
    modal.querySelector('.cancel').addEventListener('click', () => modal.remove());
}

// Профиль
async function renderProfile() {
    const content = document.getElementById('main-content');
    const level = currentUser.level || 1;
    const maxElo = 2400;
    const eloPercent = (currentUser.elo / maxElo) * 100;
    
    content.innerHTML = `
        <div class="profile-header" id="profileHeader" style="background: ${getThemeColor(currentUser.theme)}">
            <div class="settings-icon" id="settingsBtn"><i class="fas fa-cog"></i></div>
            <div style="display:flex;align-items:center;gap:15px">
                <div class="avatar-container">
                    <img src="avatar_${currentUser.avatar}.png" class="profile-avatar" onerror="this.src='https://via.placeholder.com/80'">
                </div>
                <div>
                    <h2>${currentUser.nickname}</h2>
                    <p>ID: ${currentUser.game_id}</p>
                </div>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value">${currentUser.avg || 0}</div><div>AVG</div></div>
            <div class="stat-card"><div class="stat-value">${currentUser.kd || 0}</div><div>KD</div></div>
            <div class="stat-card"><div class="stat-value">${currentUser.kills || 0}</div><div>Kills</div></div>
        </div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value">${currentUser.assists || 0}</div><div>Assists</div></div>
            <div class="stat-card"><div class="stat-value">${currentUser.deaths || 0}</div><div>Deaths</div></div>
            <div class="stat-card"><div class="stat-value">${currentUser.wr || 0}%</div><div>WR</div></div>
        </div>
        <div>
            <div style="display:flex;justify-content:space-between"><span>Уровень ${level}</span><span>${currentUser.elo} ELO</span></div>
            <div class="elo-bar"><div class="elo-fill" style="width:${eloPercent}%"></div></div>
        </div>
        <div style="margin-top:20px;background:rgba(0,0,0,0.3);border-radius:20px;padding:15px">
            <div>📅 Регистрация: ${new Date(currentUser.registered_at).toLocaleDateString()}</div>
            <div>🎮 Сыграно: ${currentUser.matches || 0} игр</div>
        </div>
    `;
    
    document.getElementById('settingsBtn').addEventListener('click', openSettings);
}

function getThemeColor(theme) {
    const themes = {
        white: 'linear-gradient(135deg, #1e2a3a, #0f1724)',
        malina: 'linear-gradient(135deg, #6b1e3a, #3a0f1e)',
        dark: '#0a0a0a',
        discord: '#5865F2',
        telegram: '#26A5E4',
        cherry: '#8B3A62'
    };
    return themes[theme] || themes.white;
}

async function openSettings() {
    const panel = document.createElement('div');
    panel.className = 'settings-panel';
    panel.innerHTML = `
        <h3>Настройки профиля</h3>
        <div style="margin:10px 0">Аватарки</div>
        <div class="settings-options" id="avatarsList"></div>
        <div style="margin:10px 0">Баннеры</div>
        <div class="settings-options" id="bannersList"></div>
        <div style="margin:10px 0">Темы</div>
        <div class="settings-options" id="themesList"></div>
        <button class="btn" style="margin-top:15px" id="closeSettings">Закрыть</button>
    `;
    document.body.appendChild(panel);
    
    const avatars = inventory.filter(i => i.type === 'avatar');
    const banners = inventory.filter(i => i.type === 'banner');
    const themes = inventory.filter(i => i.type === 'theme');
    
    avatars.forEach(a => {
        const div = document.createElement('div');
        div.className = 'settings-item';
        div.innerHTML = `<img src="${a.icon}" style="width:50px;border-radius:50%"><div>${a.name}</div>`;
        div.addEventListener('click', () => applyItem('avatar', a.id));
        document.getElementById('avatarsList').appendChild(div);
    });
    
    document.getElementById('closeSettings').addEventListener('click', () => panel.remove());
}

async function applyItem(type, itemId) {
    await fetch('/api/apply_item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_id: currentUser.telegram_id, item_type: type, item_id: itemId })
    });
    tg.showAlert?.('Применено!') || alert('Готово');
    location.reload();
}

// Пополнение монет
function openDepositModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>ПОПОЛНЕНИЕ</h3>
            <div class="cases-grid" style="display:block">
                <div class="case-card" data-stars="25">
                    <div>⭐ 25 TG STARS</div>
                    <div>💎 +1000 Test Coins</div>
                    <button class="btn" style="margin-top:10px">Выбрать</button>
                </div>
                <div class="case-card" data-stars="50">
                    <div>⭐ 50 TG STARS</div>
                    <div>💎 +2000 Test Coins</div>
                    <button class="btn" style="margin-top:10px">Выбрать</button>
                </div>
            </div>
            <button class="modal-btn cancel" style="margin-top:15px">Закрыть</button>
        </div>
    `;
    document.body.appendChild(modal);
    
    modal.querySelectorAll('.case-card').forEach(card => {
        card.addEventListener('click', async () => {
            const stars = parseInt(card.dataset.stars);
            const res = await fetch('/api/create_stars_invoice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ telegram_id: currentUser.telegram_id, stars: stars })
            });
            const data = await res.json();
            if (data.success && data.url) {
                tg.openInvoice?.(data.url, () => {}) || window.open(data.url);
            }
        });
    });
    modal.querySelector('.cancel').addEventListener('click', () => modal.remove());
}

// Хелперы
async function loadInventory() {
    const res = await fetch(`/api/inventory/${currentUser.telegram_id}`);
    inventory = await res.json();
}

function updateBalance() {
    document.getElementById('balanceAmount').innerText = currentUser?.coins || 0;
}

setInterval(() => {
    if (currentUser) updateBalance();
}, 5000);
