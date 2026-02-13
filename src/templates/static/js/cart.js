// Show a brief error toast for cart actions
function showCartError(message) {
    const existing = document.getElementById('cart-error-toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.id = 'cart-error-toast';
    toast.className = 'fixed top-20 right-6 bg-red-50 border border-red-200 text-red-800 px-4 py-2.5 rounded-xl shadow-lg z-[999] text-sm font-medium';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.4s'; }, 3000);
    setTimeout(() => toast.remove(), 3400);
}

// Cart management
async function loadCart() {
    try {
        const res = await fetch('/api/cart', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            updateCartBadge(data);
            refreshCartDrawer(data);
        }
    } catch (e) {}
}

function updateCartBadge(data) {
    const badge = document.getElementById('cart-count');
    if (!badge) return;
    const count = data.total_items || 0;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('hidden');
        badge.classList.remove('cart-badge-bounce');
        void badge.offsetWidth;
        badge.classList.add('cart-badge-bounce');
    } else {
        badge.classList.add('hidden');
    }
}

function refreshCartDrawer(data) {
    const content = document.getElementById('cart-drawer-content');
    const footer = document.getElementById('cart-drawer-footer');
    const totalEl = document.getElementById('cart-drawer-total');
    if (!content) return;

    if (!data.items || data.items.length === 0) {
        content.innerHTML = '<p class="text-gray-500 text-center py-12">Кошик порожній</p>';
        if (footer) footer.classList.add('hidden');
        return;
    }

    let html = '<div class="space-y-4">';
    data.items.forEach(item => {
        const isBundle = item.type === 'bundle';
        const imgSrc = isBundle ? item.bundle_image : item.product_image;
        const title = isBundle ? (item.bundle_name || item.name || '') : (item.product_name || '');
        const bgClass = isBundle ? 'bg-brand-50' : 'bg-gray-50';
        const subInfo = isBundle
            ? (item.bundle_items || []).map(bi => `<span class="text-xs text-gray-400">${bi.quantity}× ${bi.product_name}</span>`).join(' ')
            : '';

        html += `
        <div class="flex items-center gap-3" id="drawer-item-${item.id}">
            <div class="w-14 h-14 rounded-lg overflow-hidden ${bgClass} shrink-0">
                ${imgSrc ? `<img src="${imgSrc}" class="w-full h-full object-cover">` : ''}
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800 line-clamp-1">${title}${isBundle ? ' <span class="text-xs text-brand-500">Набiр</span>' : ''}</p>
                ${subInfo ? `<p class="text-xs text-gray-400 line-clamp-1 mt-0.5">${subInfo}</p>` : ''}
                <div class="flex items-center gap-2 mt-1">
                    <button onclick="drawerUpdateQty(${item.id}, ${item.quantity - 1})" class="w-6 h-6 flex items-center justify-center rounded bg-gray-100 text-gray-600 text-xs hover:bg-gray-200">-</button>
                    <span class="text-xs font-medium">${item.quantity}</span>
                    <button onclick="drawerUpdateQty(${item.id}, ${item.quantity + 1})" class="w-6 h-6 flex items-center justify-center rounded bg-gray-100 text-gray-600 text-xs hover:bg-gray-200">+</button>
                </div>
            </div>
            <div class="text-right shrink-0">
                <p class="text-sm font-semibold">${item.line_total} грн</p>
                <button onclick="drawerRemoveItem(${item.id})" class="text-xs text-gray-400 hover:text-red-500 mt-0.5">Видалити</button>
            </div>
        </div>`;
    });
    html += '</div>';
    content.innerHTML = html;

    if (footer) footer.classList.remove('hidden');
    if (totalEl) totalEl.textContent = data.total_price + ' грн';
}

async function drawerUpdateQty(itemId, newQty) {
    if (newQty <= 0) { drawerRemoveItem(itemId); return; }
    try {
        const res = await fetch('/api/cart/update/' + itemId, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ quantity: newQty })
        });
        if (res.ok) {
            const data = await res.json();
            updateCartBadge(data);
            refreshCartDrawer(data);
        }
    } catch (e) {}
}

async function drawerRemoveItem(itemId) {
    try {
        const res = await fetch('/api/cart/remove/' + itemId, {
            method: 'DELETE',
            credentials: 'include'
        });
        if (res.ok) {
            const data = await res.json();
            updateCartBadge(data);
            refreshCartDrawer(data);
        }
    } catch (e) {}
}

// Quick add to cart (from product cards)
async function quickAddToCart(productId, btn) {
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>';

    try {
        const res = await fetch('/api/cart/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ product_id: productId, quantity: 1 })
        });
        if (res.ok) {
            const data = await res.json();
            updateCartBadge(data);
            refreshCartDrawer(data);
            openCartDrawer();
            btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Додано!';
            setTimeout(() => { btn.innerHTML = origHTML; btn.disabled = false; }, 1500);
        } else {
            btn.innerHTML = origHTML;
            btn.disabled = false;
            showCartError('Не вдалося додати товар до кошика');
        }
    } catch (e) {
        btn.innerHTML = origHTML;
        btn.disabled = false;
        showCartError('Помилка мережі');
    }
}

// Quick add bundle to cart (from bundle cards)
async function quickAddBundle(bundleId, btn) {
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>';

    try {
        const res = await fetch('/api/cart/add-bundle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ bundle_id: bundleId, quantity: 1 })
        });
        if (res.ok) {
            const data = await res.json();
            updateCartBadge(data);
            refreshCartDrawer(data);
            openCartDrawer();
            btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Додано!';
            setTimeout(() => { btn.innerHTML = origHTML; btn.disabled = false; }, 1500);
        } else {
            btn.innerHTML = origHTML;
            btn.disabled = false;
            showCartError('Набір недоступний або вже немає в наявності');
        }
    } catch (e) {
        btn.innerHTML = origHTML;
        btn.disabled = false;
        showCartError('Помилка мережі');
    }
}

// Open cart drawer (used after adding item)
function openCartDrawer() {
    if (typeof toggleCartDrawer === 'function') {
        const drawer = document.getElementById('cart-drawer');
        if (drawer && !drawer.classList.contains('open')) {
            toggleCartDrawer();
        }
    }
}

// Load cart on page load
document.addEventListener('DOMContentLoaded', loadCart);
