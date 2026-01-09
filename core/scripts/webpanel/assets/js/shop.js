/**
 * Shop Management JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const pageContent = document.querySelector('.page-content');
    
    if (!pageContent) {
        console.error('Page content not found');
        return;
    }
    
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

    console.log('Shop URLs:', urls);

    // ==================== INIT ====================
    
    loadClientBotStatus();
    loadTariffs();
    loadPromos();
    loadCustomers();
    loadStats();

    // ==================== CLIENT BOT ====================

    async function loadClientBotStatus() {
        const statusDot = document.getElementById('clientbot-status-dot');
        const statusText = document.getElementById('clientbot-status-text');
        const btnStart = document.getElementById('btn-start-clientbot');
        const btnStop = document.getElementById('btn-stop-clientbot');
        const btnRestart = document.getElementById('btn-restart-clientbot');
        
        try {
            const response = await fetch(urls.clientbotStatus);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            console.log('Client bot status:', data);
            
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
            document.getElementById('support_username').value = config.support_username || '';
            document.getElementById('trial_days').value = config.trial_days || 3;
            document.getElementById('trial_traffic_gb').value = config.trial_traffic_gb || 999999;
            
        } catch (error) {
            console.error('Error loading client bot status:', error);
            statusDot.className = 'status-dot stopped';
            statusText.textContent = 'Ошибка загрузки';
            btnStart.disabled = false;
            btnStop.disabled = true;
            btnRestart.disabled = true;
        }
    }

    // Start client bot
    document.getElementById('btn-start-clientbot').addEventListener('click', async function() {
        const token = document.getElementById('bot_token').value;
        if (!token || token === '***') {
            showToast('Введите Bot Token', 'error');
            return;
        }
        
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Запуск...';
        
        try {
            const response = await fetch(urls.clientbotStart, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getConfigFormData())
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast('Бот запущен!', 'success');
                loadClientBotStatus();
            } else {
                showToast(data.detail || 'Ошибка запуска', 'error');
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-play"></i> Запустить';
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-play"></i> Запустить';
        }
    });

    // Stop client bot
    document.getElementById('btn-stop-clientbot').addEventListener('click', async function() {
        if (!confirm('Остановить клиентский бот?')) return;
        
        this.disabled = true;
        
        try {
            const response = await fetch(urls.clientbotStop, { method: 'POST' });
            if (response.ok) {
                showToast('Бот остановлен', 'success');
                loadClientBotStatus();
            } else {
                const data = await response.json();
                showToast(data.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
        
        this.disabled = false;
    });

    // Restart client bot
    document.getElementById('btn-restart-clientbot').addEventListener('click', async function() {
        this.disabled = true;
        
        try {
            const response = await fetch(urls.clientbotRestart, { method: 'POST' });
            if (response.ok) {
                showToast('Бот перезапущен', 'success');
                loadClientBotStatus();
            } else {
                const data = await response.json();
                showToast(data.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
        
        this.disabled = false;
    });

    // Save config (form submit)
    document.getElementById('clientbot-config-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
        
        try {
            const response = await fetch(urls.clientbotConfig, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getConfigFormData())
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast('Настройки сохранены!', 'success');
                loadClientBotStatus();
            } else {
                showToast(data.detail || 'Ошибка сохранения', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
        
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    });

    function getConfigFormData() {
        return {
            bot_token: document.getElementById('bot_token').value,
            support_username: document.getElementById('support_username').value,
            trial_days: parseInt(document.getElementById('trial_days').value) || 3,
            trial_traffic_gb: parseInt(document.getElementById('trial_traffic_gb').value) || 999999
        };
    }

    // ==================== TARIFFS ====================

    async function loadTariffs() {
        try {
            const response = await fetch(urls.tariffs);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            console.log('Tariffs:', data);
            
            const tbody = document.querySelector('#tariffs-table tbody');
            tbody.innerHTML = '';
            
            let activeCount = 0;
            
            if (data.tariffs && data.tariffs.length > 0) {
                data.tariffs.forEach(t => {
                    if (t.is_active) activeCount++;
                    
                    const typeLabel = t.type === 'traffic' 
                        ? '<span class="tariff-badge traffic">📦 Трафик</span>'
                        : '<span class="tariff-badge time">📅 Время</span>';
                    
                    const valueLabel = t.type === 'traffic'
                        ? `${t.traffic_gb || 0} GB`
                        : `${t.days || 0} дней`;
                    
                    const statusLabel = t.is_active
                        ? '<span class="badge bg-success">Активен</span>'
                        : '<span class="badge bg-secondary">Неактивен</span>';
                    
                    const row = `
                        <tr>
                            <td><strong>${escapeHtml(t.name)}</strong></td>
                            <td>${typeLabel}</td>
                            <td>${valueLabel}</td>
                            <td>${t.price_stars || 0} ⭐</td>
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
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Нет тарифов</td></tr>';
            }
            
            document.getElementById('stat-tariffs').textContent = activeCount;
            
            // Attach delete handlers
            document.querySelectorAll('.delete-tariff-btn').forEach(btn => {
                btn.addEventListener('click', async function() {
                    if (!confirm('Удалить тариф?')) return;
                    
                    const tariffId = this.dataset.id;
                    this.disabled = true;
                    
                    try {
                        const response = await fetch(`${urls.tariffs}/${tariffId}`, { method: 'DELETE' });
                        if (response.ok) {
                            showToast('Тариф удалён', 'success');
                            loadTariffs();
                        } else {
                            const data = await response.json();
                            showToast(data.detail || 'Ошибка', 'error');
                        }
                    } catch (error) {
                        showToast('Ошибка: ' + error.message, 'error');
                    }
                    
                    this.disabled = false;
                });
            });
            
        } catch (error) {
            console.error('Error loading tariffs:', error);
            document.querySelector('#tariffs-table tbody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Ошибка загрузки</td></tr>';
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
            price_stars: parseInt(formData.get('price_stars')),
            traffic_gb: formData.get('tariff_type') === 'traffic' ? parseInt(formData.get('traffic_gb')) : null,
            days: formData.get('tariff_type') === 'time' ? parseInt(formData.get('days')) : null
        };
        
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        
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
        
        submitBtn.disabled = false;
    });

    // ==================== PROMOS ====================

    async function loadPromos() {
        try {
            const response = await fetch(urls.promos);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            console.log('Promos:', data);
            
            const tbody = document.querySelector('#promos-table tbody');
            tbody.innerHTML = '';
            
            if (data.promos && data.promos.length > 0) {
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
                            <td>${p.uses_count || 0} / ${p.max_uses}</td>
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
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Нет промокодов</td></tr>';
            }
            
            // Attach delete handlers
            document.querySelectorAll('.delete-promo-btn').forEach(btn => {
                btn.addEventListener('click', async function() {
                    if (!confirm('Удалить промокод?')) return;
                    
                    const code = this.dataset.code;
                    this.disabled = true;
                    
                    try {
                        const response = await fetch(`${urls.promos}/${code}`, { method: 'DELETE' });
                        if (response.ok) {
                            showToast('Промокод удалён', 'success');
                            loadPromos();
                        } else {
                            const data = await response.json();
                            showToast(data.detail || 'Ошибка', 'error');
                        }
                    } catch (error) {
                        showToast('Ошибка: ' + error.message, 'error');
                    }
                    
                    this.disabled = false;
                });
            });
            
        } catch (error) {
            console.error('Error loading promos:', error);
            document.querySelector('#promos-table tbody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Ошибка загрузки</td></tr>';
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
        
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        
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
        
        submitBtn.disabled = false;
    });

    // ==================== CUSTOMERS ====================

    async function loadCustomers() {
        try {
            const response = await fetch(urls.customers);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            console.log('Customers:', data);
            
            const tbody = document.querySelector('#customers-table tbody');
            tbody.innerHTML = '';
            
            document.getElementById('stat-customers').textContent = data.customers ? data.customers.length : 0;
            
            if (data.customers && data.customers.length > 0) {
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
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Нет клиентов</td></tr>';
            }
            
        } catch (error) {
            console.error('Error loading customers:', error);
            document.querySelector('#customers-table tbody').innerHTML = 
                '<tr><td colspan="5" class="text-center text-danger">Ошибка загрузки</td></tr>';
        }
    }

    // ==================== STATS ====================

    async function loadStats() {
        try {
            const response = await fetch(urls.paymentsStats);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            console.log('Stats:', data);
            
            let totalRevenue = 0;
            let totalPayments = 0;
            
            if (data.stats) {
                for (const method in data.stats) {
                    totalRevenue += data.stats[method].total || 0;
                    totalPayments += data.stats[method].count || 0;
                }
            }
            
            document.getElementById('stat-revenue').textContent = `${totalRevenue}⭐`;
            document.getElementById('stat-payments').textContent = totalPayments;
            
        } catch (error) {
            console.error('Error loading stats:', error);
            document.getElementById('stat-revenue').textContent = '—';
            document.getElementById('stat-payments').textContent = '—';
        }
    }

    // ==================== HELPERS ====================

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
