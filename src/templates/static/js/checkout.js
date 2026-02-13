// Toast notification helper
function showToast(message, type = 'error') {
    const existing = document.getElementById('validation-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'validation-toast';
    const bgClass = type === 'error'
        ? 'bg-red-50 border-red-200 text-red-800'
        : 'bg-green-50 border-green-200 text-green-800';
    toast.className = `fixed top-20 right-6 ${bgClass} px-5 py-3 rounded-xl shadow-lg z-50 max-w-sm border fade-in`;
    toast.innerHTML = `<div class="flex items-center gap-2">
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span class="text-sm font-medium">${message}</span>
    </div>`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.5s'; }, 4000);
    setTimeout(() => toast.remove(), 4500);
}

// Phone input mask
const phoneInput = document.getElementById('checkout-phone');
if (phoneInput && typeof Inputmask !== 'undefined') {
    Inputmask({
        mask: '+380 99-999-99-99',
        placeholder: '_',
        showMaskOnHover: false,
        showMaskOnFocus: true,
    }).mask(phoneInput);
}

// Nova Poshta city search
let searchTimeout = null;
const citySearch = document.getElementById('np-city-search');
const cityDropdown = document.getElementById('np-city-dropdown');

if (citySearch) {
    citySearch.addEventListener('input', function () {
        clearTimeout(searchTimeout);
        const q = this.value.trim();
        if (q.length < 2) { cityDropdown.classList.add('hidden'); return; }

        searchTimeout = setTimeout(async () => {
            try {
                const res = await fetch('/delivery/np/cities?q=' + encodeURIComponent(q));
                const data = await res.json();
                if (data.length > 0) {
                    cityDropdown.innerHTML = data.map(c =>
                        `<div class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer text-sm transition"
                              onclick="selectCity('${c.ref}', '${c.name.replace(/'/g, "\\'")}')">
                            ${c.name}${c.area ? ' <span class=text-gray-400>(' + c.area + ' обл.)</span>' : ''}
                        </div>`
                    ).join('');
                    cityDropdown.classList.remove('hidden');
                } else {
                    cityDropdown.innerHTML = '<div class="px-4 py-3 text-sm text-gray-400">Нічого не знайдено</div>';
                    cityDropdown.classList.remove('hidden');
                }
            } catch (e) {}
        }, 300);
    });

    document.addEventListener('click', function (e) {
        if (!citySearch.contains(e.target) && !cityDropdown.contains(e.target)) {
            cityDropdown.classList.add('hidden');
        }
    });
}

function selectCity(ref, name) {
    document.getElementById('np-city-search').value = name;
    document.getElementById('np-city-name').value = name;
    document.getElementById('np-city-ref').value = ref;
    document.getElementById('np-city-dropdown').classList.add('hidden');
    // Reset warehouse selection
    const whSearch = document.getElementById('np-warehouse-search');
    if (whSearch) {
        whSearch.value = '';
        whSearch.disabled = true;
        whSearch.placeholder = 'Завантаження...';
    }
    const whValue = document.getElementById('np-warehouse-value');
    const whRef = document.getElementById('np-warehouse-ref');
    if (whValue) whValue.value = '';
    if (whRef) whRef.value = '';
    loadWarehouses(ref);
}

// Warehouse search (Task 2 + Task 7)
let allWarehouses = [];

async function loadWarehouses(cityRef) {
    const searchInput = document.getElementById('np-warehouse-search');
    const dropdown = document.getElementById('np-warehouse-dropdown');
    const valueInput = document.getElementById('np-warehouse-value');
    const refInput = document.getElementById('np-warehouse-ref');

    if (!searchInput) return;

    searchInput.disabled = true;
    searchInput.value = '';
    searchInput.placeholder = 'Завантаження...';
    if (valueInput) valueInput.value = '';
    if (refInput) refInput.value = '';
    allWarehouses = [];

    try {
        const res = await fetch('/delivery/np/warehouses?city_ref=' + encodeURIComponent(cityRef));
        const data = await res.json();
        allWarehouses = data;

        if (data.length > 0) {
            searchInput.disabled = false;
            searchInput.placeholder = 'Почніть вводити номер або назву відділення...';
        } else {
            searchInput.placeholder = 'Відділень не знайдено';
        }
    } catch (e) {
        searchInput.placeholder = 'Помилка завантаження';
    }
}

// Warehouse search input handler
const warehouseSearch = document.getElementById('np-warehouse-search');
const warehouseDropdown = document.getElementById('np-warehouse-dropdown');

if (warehouseSearch) {
    warehouseSearch.addEventListener('input', function () {
        const q = this.value.trim().toLowerCase();
        if (!allWarehouses.length) return;

        const filtered = q.length === 0
            ? allWarehouses.slice(0, 50)
            : allWarehouses.filter(w =>
                w.description.toLowerCase().includes(q) ||
                w.number.toString().includes(q) ||
                (w.short_address && w.short_address.toLowerCase().includes(q))
            );

        if (filtered.length > 0) {
            warehouseDropdown.innerHTML = filtered.slice(0, 50).map(w => {
                let label = w.description;
                if (w.short_address && !label.includes(w.short_address)) {
                    label += ' (' + w.short_address + ')';
                }
                const safeLabel = label.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                return `<div class="px-4 py-2.5 hover:bg-brand-50 cursor-pointer text-sm transition"
                              onclick="selectWarehouse('${w.ref}', '${safeLabel}')">
                            ${label}
                        </div>`;
            }).join('');
            warehouseDropdown.classList.remove('hidden');
        } else {
            warehouseDropdown.innerHTML = '<div class="px-4 py-3 text-sm text-gray-400">Нічого не знайдено</div>';
            warehouseDropdown.classList.remove('hidden');
        }
    });

    warehouseSearch.addEventListener('focus', function () {
        if (allWarehouses.length > 0 && !this.value.trim()) {
            warehouseSearch.dispatchEvent(new Event('input'));
        }
    });

    document.addEventListener('click', function (e) {
        if (!warehouseSearch.contains(e.target) && !warehouseDropdown.contains(e.target)) {
            warehouseDropdown.classList.add('hidden');
        }
    });
}

function selectWarehouse(ref, label) {
    const decoded = label.replace(/&quot;/g, '"');
    document.getElementById('np-warehouse-search').value = decoded;
    document.getElementById('np-warehouse-value').value = decoded;
    document.getElementById('np-warehouse-ref').value = ref;
    document.getElementById('np-warehouse-dropdown').classList.add('hidden');
}

// Switch delivery method (NP / UP)
function switchDelivery(method) {
    document.getElementById('np-fields').classList.toggle('hidden', method !== 'np');
    document.getElementById('up-fields').classList.toggle('hidden', method !== 'up');
}

// Switch NP delivery sub-type (warehouse / address)
function switchNpType(type) {
    document.getElementById('np-warehouse-block').classList.toggle('hidden', type !== 'warehouse');
    document.getElementById('np-address-block').classList.toggle('hidden', type !== 'address');
}

// Coupon validation
function parsePrice(text) {
    if (!text) return 0;
    const normalized = String(text).replace(/[^\d.,-]/g, '').replace(',', '.');
    const parsed = parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
}

async function applyCoupon() {
    const code = document.getElementById('coupon-input').value.trim();
    const resultEl = document.getElementById('coupon-result');
    const subtotalEl = document.getElementById('subtotal-amount');
    const totalEl = document.getElementById('checkout-total');
    if (!code) return;

    const subtotal = parsePrice(subtotalEl ? subtotalEl.textContent : totalEl.textContent);
    const ptAttr = document.getElementById('coupon-section')?.dataset.productsTotal;
    const productsTotal = (ptAttr != null && ptAttr !== '') ? parseFloat(ptAttr) : subtotal;

    try {
        const res = await fetch('/coupons/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ code: code, cart_total: subtotal, products_total: productsTotal })
        });
        const data = await res.json();
        resultEl.classList.remove('hidden');

        if (data.valid) {
            const discount = Number(data.estimated_discount || 0);
            const newTotal = Math.max(0, subtotal - discount);

            resultEl.className = 'mt-2 text-sm text-green-600';
            resultEl.textContent = 'Купон застосовано! Знижка: ' + discount.toFixed(2) + ' грн';
            document.getElementById('discount-row').classList.remove('hidden');
            document.getElementById('discount-amount').textContent = '-' + discount.toFixed(2) + ' грн';

            if (totalEl) {
                totalEl.textContent = newTotal.toFixed(2) + ' грн';
            }
        } else {
            resultEl.className = 'mt-2 text-sm text-red-600';
            resultEl.textContent = data.message || 'Недійсний купон';
            document.getElementById('discount-row').classList.add('hidden');
            if (totalEl) {
                totalEl.textContent = subtotal.toFixed(2) + ' грн';
            }
        }
    } catch (e) {
        console.error('Coupon error:', e);
        resultEl.classList.remove('hidden');
        resultEl.className = 'mt-2 text-sm text-red-600';
        resultEl.textContent = 'Помилка перевірки купону';
    }
}

// Form validation
const form = document.getElementById('checkout-form');
if (form) {
    form.addEventListener('submit', function (e) {
        // Phone validation
        if (phoneInput && phoneInput.inputmask) {
            const raw = phoneInput.inputmask.unmaskedvalue();
            if (raw.length < 9) {
                e.preventDefault();
                showToast('Будь ласка, введіть коректний номер телефону');
                return;
            }
        }

        // Email validation
        const emailInput = document.getElementById('checkout-email');
        if (emailInput && emailInput.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailInput.value.trim())) {
                e.preventDefault();
                showToast('Будь ласка, введіть коректний email');
                return;
            }
        }

        const method = document.querySelector('input[name="delivery_method"]:checked').value;
        if (method === 'nova_poshta') {
            if (!document.getElementById('np-city-ref').value) {
                e.preventDefault();
                showToast('Будь ласка, оберіть місто доставки');
                return;
            }
            const npType = document.querySelector('input[name="np_delivery_type"]:checked').value;
            if (npType === 'warehouse') {
                const whValue = document.getElementById('np-warehouse-value');
                if (!whValue || !whValue.value) {
                    e.preventDefault();
                    showToast('Будь ласка, оберіть відділення');
                    return;
                }
            } else {
                const npAddr = document.getElementById('np-address-input');
                if (!npAddr || !npAddr.value.trim()) {
                    e.preventDefault();
                    showToast('Будь ласка, вкажіть адресу доставки');
                    return;
                }
            }
        } else {
            const city = document.querySelector('input[name="up_city"]');
            const addr = document.querySelector('input[name="address"]');
            if (!city || !city.value.trim()) {
                e.preventDefault();
                showToast('Будь ласка, вкажіть місто');
                return;
            }
            if (!addr || !addr.value.trim()) {
                e.preventDefault();
                showToast('Будь ласка, вкажіть адресу або відділення');
                return;
            }
        }

        const btn = document.getElementById('submit-order-btn');
        btn.disabled = true;
        btn.textContent = 'Оформлення...';
    });
}
