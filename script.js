let tg = window.Telegram.WebApp;
let userId = tg.initDataUnsafe?.user?.id || null;
let user = tg.initDataUnsafe?.user || {};

let currentCoins = 0;

// Вспомогательные функции
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    document.querySelectorAll('.menu-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.menu-btn[data-page="${pageId.replace('Page','')}"]`).classList.add('active');
    if (pageId === 'profilePage') loadProfile();
    if (pageId === 'inventoryPage') loadInventory();
    if (pageId === 'casesPage') loadCasesShop();
    updateAllCoins();
}

async function post(action, data = {}) {
    data.action = action;
    data.user_id = userId;
    const resp = await fetch('/webapp', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    if (!resp.ok) throw new Error(await resp.text());
    return await resp.json();
}

async function updateAllCoins() {
    const profile = await post('get_profile');
    if (profile && profile.coins !== undefined) {
        currentCoins = profile.coins;
        document.querySelectorAll('[id^="coinBalance"]').forEach(el => el.innerText = currentCoins);
    }
}

// Регистрация
document.getElementById('registerBtn')?.addEventListener('click', async () => {
    const nickname = document.getElementById('regNickname').value.trim();
    const gameId = document.getElementById('regGameId').value.trim();
    if (nickname.length < 2 || nickname.length > 14 || !/^[a-zA-Zа-яА-Я0-9]+$/.test(nickname)) {
        tg.showAlert('Никнейм должен быть 2-14 символов, буквы/цифры');
        return;
    }
    if (gameId.length < 2 || gameId.length > 14 || !/^[a-zA-Z0-9]+$/.test(gameId)) {
        tg.showAlert('Game ID 2-14 символов, только латиница и цифры');
        return;
    }
    try {
        await post('register', { nickname, game_id: gameId, username: user.username || '' });
        tg.showAlert('Регистрация успешна!');
        showPage('mainPage');
        loadDrops();
        updateAllCoins();
        loadProfile();
    } catch(e) {
        tg.showAlert('Ошибка: ' + e.message);
    }
});

// Главная: карусель выпадающих предметов (имитация)
function loadDrops() {
    const container = document.getElementById('dropsContainer');
    if (!container) return;
    const items = ['Banner Sakura', 'Theme Discord', 'Ramka Faceit', 'Banner Hellin Frozen'];
    container.innerHTML = '';
    for (let i=0; i<6; i++) {
        const randomItem = items[Math.floor(Math.random()*items.length)];
        const card = document.createElement('div');
        card.className = 'drop-card';
        card.innerHTML = `<img src="${randomItem.toLowerCase().replace(/ /g,'')}.jpg" onerror="this.src='default.png'"><div>${randomItem}</div>`;
        container.appendChild(card);
    }
    // плавная прокрутка
    let pos = 0;
    setInterval(() => {
        pos += 1;
        container.scrollLeft = pos;
        if (pos >= container.scrollWidth - container.clientWidth) pos = 0;
    }, 3000);
}

// Задание
document.getElementById('taskStartBtn')?.addEventListener('click', async () => {
    try {
        const res = await post('complete_task', { task: 'view_profile' });
        if (res === "Task completed, case added") {
            tg.showAlert('Задание выполнено! Вы получили кейс "Loser Check" и 10 монет!');
            updateAllCoins();
            loadInventory();
        } else {
            tg.showAlert('Вы уже выполнили это задание!');
        }
        showPage('profilePage');
    } catch(e) {
        tg.showAlert('Ошибка: ' + e.message);
    }
});

// Инвентарь
async function loadInventory() {
    const inv = await post('get_inventory');
    const container = document.getElementById('inventoryList');
    container.innerHTML = '';
    for (let item of inv) {
        const div = document.createElement('div');
        div.className = 'inv-item';
        if (item.is_new) div.innerHTML += '<div class="new-badge">NEW</div>';
        const iconName = (item.item_name.toLowerCase().replace(/ /g,'') + '.jpg').replace('case','').replace('banner','');
        div.innerHTML += `<img src="${iconName}" onerror="this.src='default.png'">`;
        div.innerHTML += `<div>${item.item_name}</div>`;
        if (item.item_type === 'case') {
            div.style.cursor = 'pointer';
            div.addEventListener('click', () => openCaseModal(item.item_name, iconName));
        } else {
            div.addEventListener('click', () => applyItem(item.item_name, item.item_type));
        }
        container.appendChild(div);
        if (item.is_new) {
            await post('mark_seen', { item_name: item.item_name });
        }
    }
}

function applyItem(itemName, itemType) {
    post('apply_item', { item_name: itemName, item_type: itemType }).then(() => {
        tg.showAlert(`Предмет ${itemName} применён!`);
        loadProfile();
    }).catch(e => tg.showAlert('Ошибка применения'));
}

// Магазин кейсов
async function loadCasesShop() {
    const shop = await post('get_cases_shop');
    const container = document.getElementById('casesShop');
    container.innerHTML = '';
    for (let c of shop) {
        const div = document.createElement('div');
        div.className = 'case-item';
        div.innerHTML = `
            <img src="${c.icon}" onerror="this.src='default.png'">
            <div>${c.name}</div>
            <div class="price">💰 ${c.price}</div>
        `;
        div.addEventListener('click', () => buyCase(c.name, c.price));
        container.appendChild(div);
    }
}

async function buyCase(name, price) {
    if (currentCoins < price) {
        tg.showAlert(`Не хватает монет! Нужно ${price}, у вас ${currentCoins}`);
        return;
    }
    try {
        await post('buy_case', { case_name: name });
        tg.showAlert(`Вы купили кейс "${name}"! Он в инвентаре.`);
        updateAllCoins();
        loadInventory();
    } catch(e) {
        tg.showAlert('Ошибка покупки: ' + e.message);
    }
}

// Открытие кейса (рулетка)
let currentCase = null;
function openCaseModal(caseName, iconUrl) {
    currentCase = caseName;
    document.getElementById('caseModalIcon').src = iconUrl;
    document.getElementById('caseModalName').innerText = caseName;
    // Заполняем трек предметами (имитация)
    const track = document.getElementById('rouletteTrack');
    track.innerHTML = '';
    const possible = ['Banner Sakura', 'Theme Discord', 'Ramka Faceit', 'Banner Hellin Frozen', 'Ramka Delete', 'Theme Leo'];
    for (let i=0; i<20; i++) {
        const it = possible[Math.floor(Math.random()*possible.length)];
        const div = document.createElement('div');
        div.className = 'roulette-item';
        div.innerHTML = `<img src="${it.toLowerCase().replace(/ /g,'')}.jpg" onerror="this.src='default.png'"><span>${it}</span>`;
        track.appendChild(div);
    }
    document.getElementById('caseModal').style.display = 'flex';
}

document.getElementById('openCaseBtn')?.addEventListener('click', async () => {
    if (!currentCase) return;
    const btn = document.getElementById('openCaseBtn');
    btn.disabled = true;
    btn.innerText = 'Крутим...';
    const track = document.getElementById('rouletteTrack');
    const randomShift = Math.floor(Math.random() * 1000) + 500;
    track.style.transform = `translateX(-${randomShift}px)`;
    setTimeout(async () => {
        const result = await post('open_case', { case_name: currentCase });
        if (result && result.won) {
            tg.showAlert(`🎉 Вам выпало: ${result.won}! 🎉`);
            loadInventory();
            updateAllCoins();
        } else {
            tg.showAlert('Ошибка открытия кейса');
        }
        document.getElementById('caseModal').style.display = 'none';
        btn.disabled = false;
        btn.innerText = 'Открыть';
        track.style.transform = '';
    }, 2500);
});

// Профиль
async function loadProfile() {
    const profile = await post('get_profile');
    if (!profile) return;
    document.getElementById('profileNickname').innerText = profile.nickname;
    document.getElementById('profileGameId').innerHTML = `ID: ${profile.game_id}`;
    document.getElementById('statAvg').innerText = profile.avg;
    document.getElementById('statKd').innerText = profile.kd;
    document.getElementById('statKills').innerText = profile.kills;
    document.getElementById('statAssists').innerText = profile.assists;
    document.getElementById('statDeaths').innerText = profile.deaths;
    document.getElementById('eloValue').innerText = profile.elo;
    const level = profile.level;
    document.getElementById('levelNum').innerText = level;
    const emojis = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟'];
    document.getElementById('levelEmoji').innerText = emojis[level-1] || '⚪';
    const eloPercent = Math.min(100, (profile.elo / 2400) * 100);
    document.getElementById('eloFill').style.width = `${eloPercent}%`;
    document.getElementById('matchesCount').innerText = profile.matches;
    document.getElementById('winrate').innerText = profile.wr;
    document.getElementById('regDate').innerText = new Date(profile.registered_at).toLocaleDateString();
    document.getElementById('profileBanner').style.backgroundImage = `url('${profile.current_banner}')`;
    document.getElementById('avatarImg').src = profile.current_avatar;
    // Применяем тему
    document.body.style.background = profile.current_theme === 'dark' ? '#0a0f1e' : '#f0f2f5';
    document.body.style.color = profile.current_theme === 'dark' ? 'white' : 'black';
    updateAllCoins();
}

// Настройки (применить из инвентаря)
document.getElementById('settingsBtn')?.addEventListener('click', () => {
    tg.showAlert('Выберите предмет из инвентаря для применения: баннер, аватар или тема');
    // можно открыть инвентарь
    showPage('inventoryPage');
});

// Пополнение
document.querySelectorAll('#addCoinsBtn, .plus-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('buyCoinsModal').style.display = 'flex';
    });
});
document.getElementById('payStarsBtn')?.addEventListener('click', () => {
    tg.openInvoice({
        title: "Пополнение Test Coins",
        description: "1000 Test Coins",
        payload: "coins_1000",
        provider_token: "",
        currency: "XTR",
        prices: [{ label: "1000 Test Coins", amount: 2500 }]
    });
    document.getElementById('buyCoinsModal').style.display = 'none';
});

// Навигация
document.querySelectorAll('.menu-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const page = btn.getAttribute('data-page');
        if (page === 'main') showPage('mainPage');
        if (page === 'inventory') showPage('inventoryPage');
        if (page === 'cases') showPage('casesPage');
        if (page === 'faceit') showPage('faceitPage');
        if (page === 'profile') showPage('profilePage');
    });
});
document.querySelectorAll('.logo-small, .logo').forEach(logo => {
    logo.addEventListener('click', () => showPage('mainPage'));
});

// Партиклы
function createParticles() {
    const container = document.getElementById('particles');
    for (let i=0; i<60; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        const size = Math.random() * 6 + 2;
        p.style.width = size + 'px';
        p.style.height = size + 'px';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDuration = Math.random() * 8 + 5 + 's';
        p.style.animationDelay = Math.random() * 10 + 's';
        p.style.opacity = Math.random() * 0.5 + 0.2;
        container.appendChild(p);
    }
}
createParticles();

// Инициализация
if (userId && tg.initDataUnsafe?.user) {
    post('get_profile').then(profile => {
        if (profile && profile.nickname) {
            showPage('mainPage');
            loadDrops();
            updateAllCoins();
            loadProfile();
        } else {
            showPage('registerPage');
        }
    }).catch(() => showPage('registerPage'));
} else {
    showPage('registerPage');
}