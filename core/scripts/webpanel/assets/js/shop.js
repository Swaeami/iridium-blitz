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

    // ==================== INIT ====================
    
    loadClientBotStatus();
    loadTariffs();
    loadPromos();
    loadCustomers();
    loadStats();

    // ==================== CLIENT BOT ====================

    const setupSection = document.getElementById('bot-setup-section');
    const settingsSection = document.getElementById('bot-settings-section');

    async function loadClientBotStatus() {
        const statusDot = document.getElementById('clientbot-status-dot');
        const statusText = document.getElementById('clientbot-status-text');
        
        try {
            const response = await fetch(urls.clientbotStatus);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            if (data.is_running) {
                // Bot is running - show settings section
                statusDot.className = 'status-dot running';
                statusText.textContent = 'Запущен';
                setupSection.classList.remove('active');
                settingsSection.classList.add('active');
                
                // Fill settings form
                const config = data.config;
                document.getElementById('support_username').value = config.support_username || '';
                document.getElementById('trial_days').value = config.trial_days || 3;
                document.getElementById('trial_traffic_gb').value = config.trial_traffic_gb || 999999;
            } else {
                // Bot is not running - show setup section
                statusDot.className = 'status-dot stopped';
                statusText.textContent = 'Остановлен';
                setupSection.classList.add('active');
                settingsSection.classList.remove('active');
            }
            
        } catch (error) {
            console.error('Error loading client bot status:', error);
            statusDot.className = 'status-dot stopped';
            statusText.textContent = 'Ошибка';
            setupSection.classList.add('active');
            settingsSection.classList.remove('active');
        }
    }

    // Start client bot
    document.getElementById('btn-start-clientbot').addEventListener('click', async function() {
        const token = document.getElementById('bot_token').value.trim();
        if (!token) {
            showToast('Введите Bot Token', 'error');
            return;
        }
        
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Запуск...';
        
        try {
            const response = await fetch(urls.clientbotStart, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bot_token: token,
                    support_username: document.getElementById('setup_support_username').value,
                    trial_days: parseInt(document.getElementById('setup_trial_days').value) || 3,
                    trial_traffic_gb: parseInt(document.getElementById('setup_trial_traffic_gb').value) || 999999
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast('Бот запущен!', 'success');
                loadClientBotStatus();
            } else {
                showToast(data.detail || 'Ошибка запуска', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
        
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-play"></i> Запустить бота';
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
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        try {
            const response = await fetch(urls.clientbotRestart, { method: 'POST' });
            if (response.ok) {
                showToast('Бот перезапущен', 'success');
            } else {
                const data = await response.json();
                showToast(data.detail || 'Ошибка', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
        
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-redo"></i> Перезапустить';
    });

    // Save settings (and restart)
    document.getElementById('btn-save-settings').addEventListener('click', async function() {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
        
        try {
            const response = await fetch(urls.clientbotConfig, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bot_token: '***', // Keep existing token
                    support_username: document.getElementById('support_username').value,
                    trial_days: parseInt(document.getElementById('trial_days').value) || 3,
                    trial_traffic_gb: parseInt(document.getElementById('trial_traffic_gb').value) || 999999
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast('Настройки сохранены, бот перезапущен', 'success');
            } else {
                showToast(data.detail || 'Ошибка сохранения', 'error');
            }
        } catch (error) {
            showToast('Ошибка: ' + error.message, 'error');
        }
        
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-save"></i> Сохранить';
    });

    // ==================== TARIFFS ====================

    // Toggle traffic limit field
    document.getElementById('tariff-type-select').addEventListener('change', function() {
        const trafficGroup = document.getElementById('traffic-limit-group');
        if (this.value === 'limited') {
            trafficGroup.classList.remove('d-none');
        } else {
            trafficGroup.classList.add('d-none');
        }
    });

    async function loadTariffs() {
        try {
            const response = await fetch(urls.tariffs);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            const tbody = document.querySelector('#tariffs-table tbody');
            tbody.innerHTML = '';
            
            let activeCount = 0;
            
            if (data.tariffs && data.tariffs.length > 0) {
                data.tariffs.forEach(t => {
                    if (t.is_active) activeCount++;
                    
                    const typeLabel = t.traffic_gb 
                        ? `<span class="tariff-badge traffic">📦 ${t.traffic_gb} GB</span>`
                        : '<span class="tariff-badge time">♾️ Безлимит</span>';
                    
                    const trafficLabel = t.traffic_gb ? `${t.traffic_gb} GB` : '♾️';
                    
                    // Format prices
                    let pricesHtml = '';
                    if (t.price_1m) pricesHtml += `1м: ${t.price_1m}⭐ `;
                    if (t.price_3m) pricesHtml += `3м: ${t.price_3m}⭐ `;
                    if (t.price_6m) pricesHtml += `6м: ${t.price_6m}⭐ `;
                    if (t.price_12m) pricesHtml += `12м: ${t.price_12m}⭐`;
                    if (!pricesHtml) pricesHtml = t.price_stars ? `${t.price_stars}⭐` : '—';
                    
                    const statusLabel = t.is_active
                        ? '<span class="badge bg-success">Активен</span>'
                        : '<span class="badge bg-secondary">Неактивен</span>';
                    
                    const row = `
                        <tr>
                            <td><strong>${escapeHtml(t.name)}</strong></td>
                            <td>${typeLabel}</td>
                            <td>${trafficLabel}</td>
                            <td><small>${pricesHtml}</small></td>
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
                });
            });
            
        } catch (error) {
            console.error('Error loading tariffs:', error);
            document.querySelector('#tariffs-table tbody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Ошибка загрузки</td></tr>';
        }
    }

    // Add tariff form
    document.getElementById('add-tariff-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const tariffType = formData.get('tariff_type');
        
        const data = {
            name: formData.get('name'),
            tariff_type: tariffType === 'limited' ? 'traffic' : 'time',
            traffic_gb: tariffType === 'limited' ? parseInt(formData.get('traffic_gb')) : null,
            price_1m: parseInt(formData.get('price_1m')) || null,
            price_3m: parseInt(formData.get('price_3m')) || null,
            price_6m: parseInt(formData.get('price_6m')) || null,
            price_12m: parseInt(formData.get('price_12m')) || null
        };
        
        if (!data.price_1m) {
            showToast('Укажите цену хотя бы за 1 месяц', 'error');
            return;
        }
        
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

    // Toggle promo fields based on type
    document.getElementById('promo-type-select').addEventListener('change', function() {
        const discountField = document.getElementById('promo-discount-field');
        const daysField = document.getElementById('promo-days-field');
        const trafficField = document.getElementById('promo-traffic-field');
        
        // Hide all
        discountField.classList.add('d-none');
        daysField.classList.add('d-none');
        trafficField.classList.add('d-none');
        
        // Show relevant one
        switch (this.value) {
            case 'discount':
                discountField.classList.remove('d-none');
                break;
            case 'free_period':
                daysField.classList.remove('d-none');
                break;
            case 'extra_traffic':
                trafficField.classList.remove('d-none');
                break;
        }
    });

    async function loadPromos() {
        try {
            const response = await fetch(urls.promos);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            const tbody = document.querySelector('#promos-table tbody');
            tbody.innerHTML = '';
            
            if (data.promos && data.promos.length > 0) {
                data.promos.forEach(p => {
                    const typeLabels = {
                        discount: '<span class="promo-type-badge discount">💸 Скидка</span>',
                        free_period: '<span class="promo-type-badge free_period">📅 Дни</span>',
                        extra_traffic: '<span class="promo-type-badge extra_traffic">📦 Трафик</span>'
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
                });
            });
            
        } catch (error) {
            console.error('Error loading promos:', error);
            document.querySelector('#promos-table tbody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Ошибка загрузки</td></tr>';
        }
    }

    // Add promo form
    document.getElementById('add-promo-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const promoType = formData.get('promo_type');
        
        if (!promoType) {
            showToast('Выберите тип промокода', 'error');
            return;
        }
        
        // Get value based on promo type
        let value;
        switch (promoType) {
            case 'discount':
                value = parseInt(formData.get('discount_percent'));
                if (!value || value < 1 || value > 100) {
                    showToast('Введите скидку от 1 до 100%', 'error');
                    return;
                }
                break;
            case 'free_period':
                value = parseInt(formData.get('free_days'));
                if (!value || value < 1) {
                    showToast('Введите количество дней', 'error');
                    return;
                }
                break;
            case 'extra_traffic':
                value = parseInt(formData.get('extra_traffic'));
                if (!value || value < 1) {
                    showToast('Введите количество GB', 'error');
                    return;
                }
                break;
        }
        
        const data = {
            code: formData.get('code') || null,
            promo_type: promoType,
            value: value,
            max_uses: parseInt(formData.get('max_uses')) || 100,
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
                // Reset dynamic fields
                document.getElementById('promo-discount-field').classList.add('d-none');
                document.getElementById('promo-days-field').classList.add('d-none');
                document.getElementById('promo-traffic-field').classList.add('d-none');
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
