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

    // Close dropdown on outside click
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
    loadWarehouses(ref);
}

let warehouseListenerAdded = false;

async function loadWarehouses(cityRef) {
    const sel = document.getElementById('np-warehouse-select');
    sel.disabled = true;
    sel.innerHTML = '<option value="">Завантаження...</option>';

    try {
        const res = await fetch('/delivery/np/warehouses?city_ref=' + encodeURIComponent(cityRef));
        const data = await res.json();
        if (data.length > 0) {
            sel.innerHTML = '<option value="">Оберіть відділення</option>' +
                data.map(w => `<option value="${w.description}" data-ref="${w.ref}">${w.description}</option>`).join('');
            sel.disabled = false;
        } else {
            sel.innerHTML = '<option value="">Відділень не знайдено</option>';
        }
    } catch (e) {
        sel.innerHTML = '<option value="">Помилка завантаження</option>';
    }

    if (!warehouseListenerAdded) {
        sel.addEventListener('change', function () {
            const opt = this.options[this.selectedIndex];
            document.getElementById('np-warehouse-ref').value = opt.dataset.ref || '';
        });
        warehouseListenerAdded = true;
    }
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
async function applyCoupon() {
    const code = document.getElementById('coupon-input').value.trim();
    const resultEl = document.getElementById('coupon-result');
    if (!code) return;

    try {
        const res = await fetch('/coupons/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ code: code, cart_total: parseFloat(document.getElementById('checkout-total').textContent) || 0 })
        });
        const data = await res.json();
        resultEl.classList.remove('hidden');

        if (data.valid) {
            resultEl.className = 'mt-2 text-sm text-green-600';
            resultEl.textContent = 'Купон застосовано! Знижка: ' + data.estimated_discount + ' грн';
            document.getElementById('discount-row').classList.remove('hidden');
            document.getElementById('discount-amount').textContent = '-' + data.estimated_discount + ' грн';
        } else {
            resultEl.className = 'mt-2 text-sm text-red-600';
            resultEl.textContent = data.message || 'Недійсний купон';
        }
    } catch (e) {
        resultEl.classList.remove('hidden');
        resultEl.className = 'mt-2 text-sm text-red-600';
        resultEl.textContent = 'Помилка перевірки купону';
    }
}

// Form validation
const form = document.getElementById('checkout-form');
if (form) {
    form.addEventListener('submit', function (e) {
        const method = document.querySelector('input[name="delivery_method"]:checked').value;
        if (method === 'nova_poshta') {
            if (!document.getElementById('np-city-ref').value) {
                e.preventDefault();
                alert('Будь ласка, оберіть місто доставки');
                return;
            }
            const npType = document.querySelector('input[name="np_delivery_type"]:checked').value;
            if (npType === 'warehouse') {
                if (!document.getElementById('np-warehouse-select').value) {
                    e.preventDefault();
                    alert('Будь ласка, оберіть відділення');
                    return;
                }
            } else {
                const npAddr = document.getElementById('np-address-input');
                if (!npAddr || !npAddr.value.trim()) {
                    e.preventDefault();
                    alert('Будь ласка, вкажіть адресу доставки');
                    return;
                }
            }
        } else {
            const city = document.querySelector('input[name="up_city"]');
            const addr = document.querySelector('input[name="address"]');
            if (!city || !city.value.trim()) {
                e.preventDefault();
                alert('Будь ласка, вкажіть місто');
                return;
            }
            if (!addr || !addr.value.trim()) {
                e.preventDefault();
                alert('Будь ласка, вкажіть адресу або відділення');
                return;
            }
        }

        const btn = document.getElementById('submit-order-btn');
        btn.disabled = true;
        btn.textContent = 'Оформлення...';
    });
}
