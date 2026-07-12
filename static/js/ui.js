/* ui.js — All interactive UI logic */
(function () {
'use strict';

// ══════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════
function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
function qsa(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }

// ══════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════
const toastContainer = qs('.toast-container');
function showToast(msg, type = 'info', duration = 3500) {
    if (!toastContainer) return;
    const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', info: 'fa-circle-info', cart: 'fa-bag-shopping' };
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${msg}</span>`;
    toastContainer.appendChild(t);
    setTimeout(() => {
        t.classList.add('out');
        t.addEventListener('animationend', () => t.remove());
    }, duration);
}

// ══════════════════════════════════════════════════════
// DARK MODE TOGGLE
// ══════════════════════════════════════════════════════
function initThemeToggle() {
    const btn = qs('#theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    });
}

// ══════════════════════════════════════════════════════
// HERO CAROUSEL
// ══════════════════════════════════════════════════════
function initCarousel() {
    const track = qs('.carousel-track');
    if (!track) return;
    const slides = qsa('.carousel-slide', track);
    if (slides.length < 2) return;
    const progressItems = qsa('.progress-item');
    const fills = qsa('.progress-fill');
    let current = 0, timer = null, fillTimer = null;
    const DURATION = 5500;

    function goTo(idx) {
        slides[current].classList.remove('active');
        progressItems[current]?.classList.remove('active');
        fills[current].style.transition = 'none';
        fills[current].style.width = '0';

        current = (idx + slides.length) % slides.length;
        track.style.transform = `translateX(-${current * 100}%)`;

        slides[current].classList.add('active');
        progressItems[current]?.classList.add('active');
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                fills[current].style.transition = `width ${DURATION}ms linear`;
                fills[current].style.width = '100%';
            });
        });
    }

    function start() {
        clearInterval(timer);
        timer = setInterval(() => goTo(current + 1), DURATION);
    }

    progressItems.forEach((item, i) => item.addEventListener('click', () => { goTo(i); start(); }));
    qs('.carousel-prev')?.addEventListener('click', () => { goTo(current - 1); start(); });
    qs('.carousel-next')?.addEventListener('click', () => { goTo(current + 1); start(); });

    // Touch swipe
    let touchX = 0;
    track.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
    track.addEventListener('touchend', e => {
        const diff = touchX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 40) { goTo(current + (diff > 0 ? 1 : -1)); start(); }
    });

    track.addEventListener('mouseenter', () => clearInterval(timer));
    track.addEventListener('mouseleave', start);

    goTo(0); start();
}

// ══════════════════════════════════════════════════════
// FLASH SALE COUNTDOWN
// ══════════════════════════════════════════════════════
function initFlashSale() {
    const display = qs('#flash-timer-end');
    if (!display) return;
    let target = localStorage.getItem('flashSaleEnd');
    if (!target || Date.now() > parseInt(target)) {
        target = Date.now() + 8 * 3600 * 1000;
        localStorage.setItem('flashSaleEnd', target);
    }

    function tick() {
        const diff = parseInt(target) - Date.now();
        if (diff <= 0) { clearInterval(id); return; }
        const h = Math.floor(diff / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        const pad = n => String(n).padStart(2, '0');
        qs('#ft-h') && (qs('#ft-h').textContent = pad(h));
        qs('#ft-m') && (qs('#ft-m').textContent = pad(m));
        qs('#ft-s') && (qs('#ft-s').textContent = pad(s));
    }
    tick();
    const id = setInterval(tick, 1000);
}

// ══════════════════════════════════════════════════════
// SEARCH OVERLAY
// ══════════════════════════════════════════════════════
function initSearch() {
    const overlay = qs('#search-overlay');
    const input = qs('#search-input');
    const resultsBox = qs('#search-results');
    if (!overlay) return;

    const openBtns = qsa('[data-search-open]');
    const closeBtns = qsa('[data-search-close]');

    function openSearch() {
        overlay.classList.add('open');
        setTimeout(() => input?.focus(), 100);
    }
    function closeSearch() { overlay.classList.remove('open'); }

    openBtns.forEach(b => b.addEventListener('click', openSearch));
    closeBtns.forEach(b => b.addEventListener('click', closeSearch));
    overlay.addEventListener('click', e => { if (e.target === overlay) closeSearch(); });

    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSearch(); });

    qsa('.trending-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            input.value = tag.textContent;
            input.dispatchEvent(new Event('input'));
        });
    });

    if (!input || !resultsBox) return;
    let debounce;
    input.addEventListener('input', () => {
        clearTimeout(debounce);
        const q = input.value.trim();
        if (q.length < 2) { resultsBox.innerHTML = ''; return; }
        debounce = setTimeout(async () => {
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
                const data = await res.json();
                resultsBox.innerHTML = data.results.map(p => `
                    <div class="search-result-item" onclick="window.location.href='/product/${p.id}'">
                        <img class="search-result-img" src="/static/images/${p.image}" alt="${p.name}">
                        <span class="search-result-name">${p.name}</span>
                        ${p.compare_at_price && parseFloat(p.compare_at_price) > parseFloat(p.price) 
                            ? `<span class="search-result-price"><span style="color:var(--text-2);text-decoration:line-through;margin-right:6px;font-size:0.9em;">৳${p.compare_at_price}</span>৳${p.price}</span>` 
                            : `<span class="search-result-price">৳${p.price}</span>`}
                    </div>`).join('') || '<p style="color:var(--text-2);font-size:.85rem;padding:.5rem 0;">No results found.</p>';
            } catch {}
        }, 300);
    });
}

// ══════════════════════════════════════════════════════
// CART DRAWER
// ══════════════════════════════════════════════════════
const CART_KEY = 'illyeen_cart';
let cart = JSON.parse(localStorage.getItem(CART_KEY) || '[]');

function saveCart() { localStorage.setItem(CART_KEY, JSON.stringify(cart)); }
function cartTotal() { return cart.reduce((s, i) => s + (parseFloat(i.price.replace(/[^0-9.]/g,'')) * i.qty), 0); }
function updateBadge() {
    const count = cart.reduce((s, i) => s + i.qty, 0);
    qsa('.cart-badge').forEach(b => { b.textContent = count; b.style.display = count ? 'flex' : 'none'; });
    qsa('.m-badge.cart-count').forEach(b => { b.textContent = count; b.style.display = count ? 'flex' : 'none'; });
}

function renderCart() {
    const itemsEl = qs('#cart-items');
    const subtotalEl = qs('#cart-subtotal');
    const shippingFill = qs('.cart-shipping-fill');
    const shippingText = qs('.cart-shipping-text');
    if (!itemsEl) return;

    const FREE_THRESHOLD = 2000;
    const total = cartTotal();
    const remaining = Math.max(0, FREE_THRESHOLD - total);
    if (shippingFill) shippingFill.style.width = Math.min(100, (total / FREE_THRESHOLD) * 100) + '%';
    if (shippingText) {
        shippingText.innerHTML = remaining > 0
            ? `Add <span>৳${remaining.toFixed(0)}</span> more for Free Shipping!`
            : `<span style="color:var(--success);">🎉 You've got Free Shipping!</span>`;
    }
    if (subtotalEl) subtotalEl.textContent = `৳${total.toFixed(2)}`;

    if (!cart.length) {
        itemsEl.innerHTML = `<div class="cart-empty"><i class="fa-solid fa-bag-shopping"></i><p>Your cart is empty.</p></div>`;
        return;
    }
    itemsEl.innerHTML = cart.map((item, idx) => `
        <div class="cart-item">
            <img class="cart-item-img" src="/static/images/${item.image}" alt="${item.name}">
            <div class="cart-item-info">
                <div class="cart-item-name">${item.name}</div>
                <div class="cart-item-price">${item.price}</div>
                <div class="cart-qty">
                    <button class="qty-btn" data-idx="${idx}" data-d="-1">−</button>
                    <span class="qty-num">${item.qty}</span>
                    <button class="qty-btn" data-idx="${idx}" data-d="1">+</button>
                </div>
                <span class="cart-item-remove" data-idx="${idx}">Remove</span>
            </div>
        </div>`).join('');

    qsa('.qty-btn', itemsEl).forEach(btn => {
        btn.addEventListener('click', () => {
            const i = parseInt(btn.dataset.idx);
            cart[i].qty += parseInt(btn.dataset.d);
            if (cart[i].qty <= 0) cart.splice(i, 1);
            saveCart(); renderCart(); updateBadge();
        });
    });
    qsa('.cart-item-remove', itemsEl).forEach(btn => {
        btn.addEventListener('click', () => {
            cart.splice(parseInt(btn.dataset.idx), 1);
            saveCart(); renderCart(); updateBadge();
            showToast('Item removed from cart.', 'info');
        });
    });
}

function initCartDrawer() {
    const overlay = qs('#cart-overlay');
    const drawer = qs('#cart-drawer');
    if (!overlay || !drawer) return;

    function openCart() { overlay.classList.add('open'); drawer.classList.add('open'); renderCart(); }
    function closeCart() { overlay.classList.remove('open'); drawer.classList.remove('open'); }

    qsa('[data-cart-open]').forEach(b => b.addEventListener('click', openCart));
    qsa('[data-cart-close]').forEach(b => b.addEventListener('click', closeCart));
    overlay.addEventListener('click', e => { if (e.target === overlay) closeCart(); });

    updateBadge();
}

// ══════════════════════════════════════════════════════
// ADD TO CART
// ══════════════════════════════════════════════════════
function addToCart(id, name, price, image, btn) {
    const formattedPrice = `৳${price}`;
    const existing = cart.find(i => i.id === id);
    if (existing) { existing.qty++; } else { cart.push({ id, name, price: formattedPrice, image, qty: 1 }); }
    saveCart(); updateBadge(); renderCart();
    showToast(`<strong>${name}</strong> added to cart.`, 'cart');

    // Button animation
    if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i>';
        btn.classList.add('done');
        setTimeout(() => { btn.innerHTML = orig; btn.classList.remove('done'); }, 1800);
    }

    // Fly-to-cart animation
    if (btn) {
        const img = btn.closest('.product-image')?.querySelector('img');
        const cartIcon = qs('.cart-wrap');
        if (img && cartIcon) {
            const srcRect = img.getBoundingClientRect();
            const dstRect = cartIcon.getBoundingClientRect();
            const flyEl = document.createElement('img');
            flyEl.src = img.src;
            flyEl.className = 'fly-img';
            flyEl.style.cssText = `width:${srcRect.width*.25}px;height:${srcRect.height*.25}px;top:${srcRect.top}px;left:${srcRect.left}px;`;
            flyEl.style.setProperty('--fly-x', `${dstRect.left - srcRect.left}px`);
            flyEl.style.setProperty('--fly-y', `${dstRect.top - srcRect.top}px`);
            document.body.appendChild(flyEl);
            flyEl.addEventListener('animationend', () => flyEl.remove());
        }
    }
}

// Expose to inline onclick handlers
window.addToCart = addToCart;

function buyNow(id, name, price, image) {
    const formattedPrice = `৳${price}`;
    const existing = cart.find(i => i.id === id);
    if (!existing) {
        cart.push({ id, name, price: formattedPrice, image, qty: 1 });
        saveCart();
        updateBadge();
    }
    window.location.href = '/checkout';
}
window.buyNow = buyNow;

// ══════════════════════════════════════════════════════
// WISHLIST
// ══════════════════════════════════════════════════════
const WISH_KEY = 'illyeen_wish';
let wishlist = JSON.parse(localStorage.getItem(WISH_KEY) || '[]');

function toggleWishlist(id, btn) {
    const idx = wishlist.indexOf(id);
    if (idx === -1) {
        wishlist.push(id);
        btn.classList.add('active');
        showToast('Added to wishlist!', 'success');
    } else {
        wishlist.splice(idx, 1);
        btn.classList.remove('active');
        showToast('Removed from wishlist.', 'info');
    }
    localStorage.setItem(WISH_KEY, JSON.stringify(wishlist));
    btn.classList.add('pop');
    btn.addEventListener('animationend', () => btn.classList.remove('pop'), { once: true });
}

function initWishlists() {
    qsa('.wishlist-btn').forEach(btn => {
        const id = btn.dataset.id;
        if (wishlist.includes(id)) btn.classList.add('active');
        btn.addEventListener('click', () => toggleWishlist(id, btn));
    });
}

// ══════════════════════════════════════════════════════
// INFINITE SCROLL
// ══════════════════════════════════════════════════════
function initInfiniteScroll() {
    const sentinel = qs('#scroll-sentinel');
    const grid = qs('#product-grid');
    const catId = qs('[data-category]')?.dataset.category;
    if (!sentinel || !grid) return;

    let page = 2, loading = false, hasMore = true;

    function createSkeleton() {
        const sk = document.createElement('div');
        sk.className = 'skeleton-card';
        sk.innerHTML = `<div class="skeleton-img"></div><div class="skeleton-line"></div><div class="skeleton-line short"></div>`;
        return sk;
    }

    function showSkeletons(n) {
        const frags = [];
        for (let i = 0; i < n; i++) { const s = createSkeleton(); frags.push(s); grid.appendChild(s); }
        return frags;
    }

    const io = new IntersectionObserver(async (entries) => {
        if (!entries[0].isIntersecting || loading || !hasMore) return;
        loading = true;
        const skels = showSkeletons(4);
        try {
            const url = `/api/products?page=${page}${catId ? `&category=${catId}` : ''}`;
            const res = await fetch(url);
            const data = await res.json();
            skels.forEach(s => s.remove());
            data.products.forEach(p => {
                const div = document.createElement('div');
                div.className = 'product-card reveal';
                div.dataset.category = p.category_id;
                const imgHtml = p.hero ? `
                    <div class="img-box" style="aspect-ratio:4/5;">
                        <img class="blur-placeholder" src="${p.hero.blur}" alt="" aria-hidden="true">
                        <picture>
                            <source type="image/webp" srcset="${p.hero.srcset}" sizes="(max-width:600px) 50vw, 25vw">
                            <img src="${p.hero.src_600}" alt="${p.hero.alt}" loading="lazy" class="blur-up" onload="this.classList.add('loaded')">
                        </picture>
                    </div>` : `<img src="/static/images/${p.image}" alt="${p.name}" loading="lazy" style="aspect-ratio:4/5;">`;

                const oosBadge = p.stock <= 0 ? `
                    <div class="oos-badge">
                        Out of Stock
                    </div>` : '';
                const quickActionsHtml = p.stock > 0 ? `
                                <button class="add-to-cart-btn" onclick="event.preventDefault();addToCart('${p.id}','${p.name}','${p.price}','${p.image}',this)">
                                    <i class="fa-solid fa-cart-shopping"></i>
                                    Add to Cart
                                </button>`
                            : `
                                <button class="out-of-stock-btn" disabled>
                                    <i class="fa-solid fa-circle-xmark"></i>
                                    Out of Stock
                                </button>`;

                div.innerHTML = `
                    <button class="wishlist-btn" data-id="${p.id}">
                        <i class="fa-regular fa-heart"></i>
                    </button>
                    <a href="/product/${p.id}" style="display:block;">
                        <div class="product-image">
                            ${imgHtml}
                            ${oosBadge}
                            <div class="product-quick">
                                ${quickActionsHtml}
                            </div>
                        </div>
                    </a>
                    <div class="product-info">
                        <h4 class="product-name">${p.name}</h4>
                        ${p.compare_at_price && parseFloat(p.compare_at_price) > parseFloat(p.price) 
                            ? `<p class="product-price">
                                <span class="price-old">৳${p.compare_at_price}</span>
                                <span class="price-new">৳${p.price}</span>
                               </p>`
                            : `<p class="product-price"><span class="price-new">৳${p.price}</span></p>`}
                        <a href="/product/${p.id}" class="view-details-btn">
                            View Details
                            <i class="fa-solid fa-arrow-right"></i>
                        </a>
                    </div>`;
                grid.insertBefore(div, sentinel);
                requestAnimationFrame(() => div.classList.add('active'));
            });
            hasMore = data.has_more;
            if (!hasMore) sentinel.remove();
            page++;
        } catch { skels.forEach(s => s.remove()); }
        loading = false;
    }, { rootMargin: '200px' });

    io.observe(sentinel);
}



// ══════════════════════════════════════════════════════
// QUICK VIEW MODAL
// ══════════════════════════════════════════════════════
function initQuickView() {
    const overlay = qs('#qv-overlay');
    if (!overlay) return;
    
    const closeBtn = qs('#qv-close');
    const triggers = qsa('.qv-trigger'); // We will add this class to buttons
    
    function closeQV() {
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    }
    
    closeBtn.addEventListener('click', closeQV);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeQV();
    });
    
    // Add logic here later to open modal and populate data
    window.openQuickView = function(id, name, price, img, desc, link) {
        qs('#qv-title').textContent = name;
        qs('#qv-price').textContent = `৳${price}`;
        qs('#qv-desc').textContent = desc || "Experience the pinnacle of luxury. Hand-crafted and strictly limited edition.";
        qs('#qv-img').src = img;
        qs('#qv-link').href = link;
        
        let cleanImage = img;
        if (img.includes('/static/images/')) {
            cleanImage = img.split('/static/images/')[1];
        }

        const addBtn = qs('#qv-add-btn');
        const buyBtn = qs('#qv-buy-btn');

        if (addBtn) {
            addBtn.onclick = function(e) {
                e.preventDefault();
                addToCart(id, name, price, cleanImage, this);
            };
        }
        if (buyBtn) {
            buyBtn.onclick = function(e) {
                e.preventDefault();
                buyNow(id, name, price, cleanImage);
            };
        }
        
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    };
}

// ══════════════════════════════════════════════════════
// MAGNETIC BUTTONS
// ══════════════════════════════════════════════════════
function initMagneticButtons() {
    const buttons = qsa('.btn:not(.magnetic)');
    buttons.forEach(btn => {
        btn.classList.add('magnetic');
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = (e.clientX - rect.left - rect.width/2) * 0.4;
            const y = (e.clientY - rect.top - rect.height/2) * 0.4;
            btn.style.transform = `translate(${x}px, ${y}px)`;
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = `translate(0px, 0px)`;
        });
    });
}

// ══════════════════════════════════════════════════════
// MOBILE NAV ACTIVE STATE
// ══════════════════════════════════════════════════════
function initMobileNav() {
    const path = window.location.pathname;
    qsa('.mobile-nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && (path === href || (href !== '/' && path.startsWith(href)))) {
            item.classList.add('active');
        }
    });
}

// ══════════════════════════════════════════════════════
// INIT ALL
// ══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initCarousel();
    initFlashSale();
    initSearch();
    initCartDrawer();
    initQuickView();
    initMagneticButtons();
    initWishlists();
    initInfiniteScroll();
    initMobileNav();
});

})();
