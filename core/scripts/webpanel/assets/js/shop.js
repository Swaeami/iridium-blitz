/**
 * Shop Management JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const pageContent = document.querySelector('.page-content');
    
    // URLs from data attributes
    const urls = {
        clientbotStatus: pageContent.dataset.clientbotStatusUrl,
        clientbotStart: pageContent.dataset.clientbotStartUrl,
        clientbotStop: pageContent.dataset.clientbotStopUrl,
        clientbotRestart: pageContent.dataset.clientbotRestartUrl,
        clientbotConfig: pageContent.dataset.clientbotConfigUrl,
        tariffs: pageContent.dataset.tariffsUrl,
        promos: pageContent.dataset.promosUrl,
        customers: pageContent.dataset.customersUrl,
        paymentsStats: pageContent.dataset.paymentsStatsUrl
    };

    // ==================== INIT ====================
    
    loadClientBotStatus();
    loadTariffs();
    loadPromos();
    loadCustomers();
    loadStats();

    // ==================== CLIENT BOT ====================

    async function loadClientBotStatus() {
        try {
            const response = await fetch(urls.clientbotStatus);
            const data = await response.json();
            
            const statusDot = document.getElementById('clientbot-status-dot');
            const statusText = document.getElementById('clientbot-status-text');
            const btnStart = document.getElementById('btn-start-clientbot');
            const btnStop = document.getElementById('btn-stop-clientbot');
            const btnRestart = document.getElementById('btn-restart-clientbot');
            
            if (data.is_running) {
                statusDot.className = 'status-dot running';
                statusText.textContent = 'Запущен';
                btnStart.disabled = true;
                btnStop.disabled = false;
                btnRestart.disabled = false;
            } else {
                statusDot.className = 'status-dot stopped';
                statusText.textContent = 'Остановлен';
                btnStart.disabled = false;
                btnStop.disabled = true;
                btnRestart.disabled = true;
            }
            
            // Fill config form
            const config = data.config;
            document.getElementById('bot_token').value = config.bot_token || '';
            document.getElementById('yookassa_shop_id').value = config.yookassa_shop_id || '';
            document.getElementById('yookassa_secret_key').value = config.yookassa_secret_key || '';
            document.getElementById('support_username').value = config.support_username || '';
            document.getElementById('trial_days').value = config.trial_days || 3;
            document.getElementById('trial_traffic_gb').value = config.trial_traffic_gb || 999999;
            
        } catch (error) {
            console.error('Error loading client bot status:', error);
        }
    }

    // Start client bot
    document.getElementById('btn-start-clientbot').addEventListener('click', async function() {
        const token = document.getElementById('bot_token').value;
        if (!token) {
            showToast('Введите Bot Token', 'error');
            return;
        }
        
        try {
            const response = await fetch(urls.clientbotStart, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getConfigFormData())
            });
            
            if (response.ok) {
                showToast('Бот запущен', 'success');
                loadClientBotStatus();
            } else {
                const data = await response.json();
                showToast(data.detail || 'Ошибка запуска', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
    });

    // Stop client bot
    document.getElementById('btn-stop-clientbot').addEventListener('click', async function() {
        if (!confirm('Остановить клиентский бот?')) return;
        
        try {
            const response = await fetch(urls.clientbotStop, { method: 'POST' });
            if (response.ok) {
                showToast('Бот остановлен', 'success');
                loadClientBotStatus();
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
    });

    // Restart client bot
    document.getElementById('btn-restart-clientbot').addEventListener('click', async function() {
        try {
            const response = await fetch(urls.clientbotRestart, { method: 'POST' });
            if (response.ok) {
                showToast('Бот перезапущен', 'success');
                loadClientBotStatus();
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
    });

    // Save config
    document.getElementById('clientbot-config-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        try {
            const response = await fetch(urls.clientbotConfig, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getConfigFormData())
            });
            
            if (response.ok) {
                showToast('Настройки сохранены', 'success');
                loadClientBotStatus();
            } else {
                const data = await response.json();
                showToast(data.detail || 'Ошибка сохранения', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
    });

    function getConfigFormData() {
        return {
            bot_token: document.getElementById('bot_token').value,
            yookassa_shop_id: document.getElementById('yookassa_shop_id').value,
            yookassa_secret_key: document.getElementById('yookassa_secret_key').value,
            support_username: document.getElementById('support_username').value,
            trial_days: parseInt(document.getElementById('trial_days').value) || 3,
            trial_traffic_gb: parseInt(document.getElementById('trial_traffic_gb').value) || 999999
        };
    }

    // ==================== TARIFFS ====================

    async function loadTariffs() {
        try {
            const response = await fetch(urls.tariffs);
            const data = await response.json();
            
            const tbody = document.querySelector('#tariffs-table tbody');
            tbody.innerHTML = '';
            
            let activeCount = 0;
            
            data.tariffs.forEach(t => {
                if (t.is_active) activeCount++;
                
                const typeLabel = t.type === 'traffic' 
                    ? '<span class="tariff-badge traffic">📦 Трафик</span>'
                    : '<span class="tariff-badge time">📅 Время</span>';
                
                const valueLabel = t.type === 'traffic'
                    ? `${t.traffic_gb} GB`
                    : `${t.days} дней`;
                
                const statusLabel = t.is_active
                    ? '<span class="badge bg-success">Активен</span>'
                    : '<span class="badge bg-secondary">Неактивен</span>';
                
                const row = `
                    <tr>
                        <td><strong>${escapeHtml(t.name)}</strong></td>
                        <td>${typeLabel}</td>
                        <td>${valueLabel}</td>
                        <td>${t.price}₽</td>
                        <td>${t.price_stars || '—'}</td>
                        <td>${statusLabel}</td>
                        <td>
                            <button class="btn btn-danger btn-sm delete-tariff-btn" data-id="${t._id}" ${!t.is_active ? 'disabled' : ''}>
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
            
            document.getElementById('stat-tariffs').textContent = activeCount;
            
            // Attach delete handlers
            document.querySelectorAll('.delete-tariff-btn').forEach(btn => {
                btn.addEventListener('click', async function() {
                    if (!confirm('Удалить тариф?')) return;
                    
                    const tariffId = this.dataset.id;
                    try {
                        const response = await fetch(`${urls.tariffs}/${tariffId}`, { method: 'DELETE' });
                        if (response.ok) {
                            showToast('Тариф удалён', 'success');
                            loadTariffs();
                        }
                    } catch (error) {
                        showToast('Ошибка: ' + error.message, 'error');
                    }
                });
            });
            
        } catch (error) {
            console.error('Error loading tariffs:', error);
        }
    }

    // Tariff type toggle
    document.getElementById('tariff-type-select').addEventListener('change', function() {
        const trafficGroup = document.getElementById('traffic-gb-group');
        const daysGroup = document.getElementById('days-group');
        
        if (this.value === 'traffic') {
            trafficGroup.classList.remove('d-none');
            daysGroup.classList.add('d-none');
        } else {
            trafficGroup.classList.add('d-none');
            daysGroup.classList.remove('d-none');
        }
    });

    // Add tariff form
    document.getElementById('add-tariff-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = {
            name: formData.get('name'),
            tariff_type: formData.get('tariff_type'),
            price: parseFloat(formData.get('price')),
            traffic_gb: formData.get('tariff_type') === 'traffic' ? parseInt(formData.get('traffic_gb')) : null,
            days: formData.get('tariff_type') === 'time' ? parseInt(formData.get('days')) : null,
            price_stars: formData.get('price_stars') ? parseInt(formData.get('price_stars')) : null
        };
        
        try {
            const response = await fetch(urls.tariffs, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                showToast('Тариф создан', 'success');
                bootstrap.Modal.getInstance(document.getElementById('addTariffModal')).hide();
                this.reset();
                loadTariffs();
            } else {
                const err = await response.json();
                showToast(err.detail || 'Ошибка создания', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
    });

    // ==================== PROMOS ====================

    async function loadPromos() {
        try {
            const response = await fetch(urls.promos);
            const data = await response.json();
            
            const tbody = document.querySelector('#promos-table tbody');
            tbody.innerHTML = '';
            
            data.promos.forEach(p => {
                const typeLabels = {
                    discount: '<span class="promo-type discount">💸 Скидка</span>',
                    free_period: '<span class="promo-type free_period">📅 Дни</span>',
                    extra_traffic: '<span class="promo-type extra_traffic">📦 Трафик</span>'
                };
                
                const valueLabels = {
                    discount: `${p.value}%`,
                    free_period: `+${p.value} дней`,
                    extra_traffic: `+${p.value} GB`
                };
                
                const expiresLabel = p.expires_at 
                    ? new Date(p.expires_at).toLocaleDateString()
                    : '∞';
                
                const statusClass = p.is_active ? '' : 'text-muted';
                
                const row = `
                    <tr class="${statusClass}">
                        <td><code>${escapeHtml(p.code)}</code></td>
                        <td>${typeLabels[p.type] || p.type}</td>
                        <td>${valueLabels[p.type] || p.value}</td>
                        <td>${p.uses_count} / ${p.max_uses}</td>
                        <td>${expiresLabel}</td>
                        <td>
                            <button class="btn btn-danger btn-sm delete-promo-btn" data-code="${escapeHtml(p.code)}" ${!p.is_active ? 'disabled' : ''}>
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
            
            // Attach delete handlers
            document.querySelectorAll('.delete-promo-btn').forEach(btn => {
                btn.addEventListener('click', async function() {
                    if (!confirm('Удалить промокод?')) return;
                    
                    const code = this.dataset.code;
                    try {
                        const response = await fetch(`${urls.promos}/${code}`, { method: 'DELETE' });
                        if (response.ok) {
                            showToast('Промокод удалён', 'success');
                            loadPromos();
                        }
                    } catch (error) {
                        showToast('Ошибка: ' + error.message, 'error');
                    }
                });
            });
            
        } catch (error) {
            console.error('Error loading promos:', error);
        }
    }

    // Promo type toggle
    document.getElementById('promo-type-select').addEventListener('change', function() {
        const label = document.getElementById('promo-value-label');
        const labels = {
            discount: 'Скидка (%)',
            free_period: 'Бесплатные дни',
            extra_traffic: 'Доп. трафик (GB)'
        };
        label.textContent = labels[this.value] || 'Значение';
    });

    // Add promo form
    document.getElementById('add-promo-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = {
            code: formData.get('code') || null,
            promo_type: formData.get('promo_type'),
            value: parseFloat(formData.get('value')),
            max_uses: parseInt(formData.get('max_uses')),
            expire_days: parseInt(formData.get('expire_days')) || null,
            description: formData.get('description') || ''
        };
        
        try {
            const response = await fetch(urls.promos, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                const result = await response.json();
                showToast(`Промокод ${result.promo.code} создан`, 'success');
                bootstrap.Modal.getInstance(document.getElementById('addPromoModal')).hide();
                this.reset();
                loadPromos();
            } else {
                const err = await response.json();
                showToast(err.detail || 'Ошибка создания', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
    });

    // ==================== CUSTOMERS ====================

    async function loadCustomers() {
        try {
            const response = await fetch(urls.customers);
            const data = await response.json();
            
            const tbody = document.querySelector('#customers-table tbody');
            tbody.innerHTML = '';
            
            document.getElementById('stat-customers').textContent = data.customers.length;
            
            data.customers.forEach(c => {
                const tgUser = c.telegram_username ? `@${c.telegram_username}` : `ID: ${c.telegram_id}`;
                const vpnUser = c.vpn_username || '—';
                const trialUsed = c.trial_used ? '✅' : '❌';
                const createdAt = c.created_at ? new Date(c.created_at).toLocaleDateString() : '—';
                const lastActive = c.last_active ? new Date(c.last_active).toLocaleDateString() : '—';
                
                const row = `
                    <tr>
                        <td>${escapeHtml(tgUser)}</td>
                        <td><code>${escapeHtml(vpnUser)}</code></td>
                        <td>${trialUsed}</td>
                        <td>${createdAt}</td>
                        <td>${lastActive}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
            
        } catch (error) {
            console.error('Error loading customers:', error);
        }
    }

    // ==================== STATS ====================

    async function loadStats() {
        try {
            const response = await fetch(urls.paymentsStats);
            const data = await response.json();
            
            let totalRevenue = 0;
            let totalPayments = 0;
            
            for (const method in data.stats) {
                totalRevenue += data.stats[method].total || 0;
                totalPayments += data.stats[method].count || 0;
            }
            
            document.getElementById('stat-revenue').textContent = `${totalRevenue}₽`;
            document.getElementById('stat-payments').textContent = totalPayments;
            
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    // ==================== HELPERS ====================

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});

