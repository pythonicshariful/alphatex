// main.js — Core page behaviours
document.addEventListener('DOMContentLoaded', () => {

    // ── Dark Mode (load from storage) ──────────────────────
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // ── Header scroll effect ────────────────────────────────
    const header = document.querySelector('header');
    if (header && !header.classList.contains('solid-header')) {
        const onScroll = () => {
            header.classList.toggle('scrolled', window.scrollY > 60);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // ── Reveal animations ───────────────────────────────────
    const reveals = document.querySelectorAll('.reveal');
    if (reveals.length) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e, i) => {
                if (e.isIntersecting) {
                    setTimeout(() => e.target.classList.add('active'), i * 80);
                    io.unobserve(e.target);
                }
            });
        }, { threshold: 0.12 });
        reveals.forEach(el => io.observe(el));
    }

    // ── Smooth Page Transitions ─────────────────────────────
    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 50);

    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            const target = this.getAttribute('target');
            
            // Ignore links with target="_blank", anchors (#), or javascript actions
            if (
                target === '_blank' || 
                e.ctrlKey || e.metaKey || 
                href.startsWith('#') || 
                href.startsWith('javascript:') ||
                this.hasAttribute('data-cart-open') ||
                this.classList.contains('qv-trigger')
            ) {
                return;
            }

            if (href && href !== '#' && !href.startsWith('mailto:') && !href.startsWith('tel:')) {
                e.preventDefault();
                document.body.classList.remove('loaded');
                document.body.classList.add('page-exit');
                
                setTimeout(() => {
                    window.location.href = href;
                }, 350); // Slightly less than 400ms CSS transition
            }
        });
    });

    // ── Parallax Scrolling ──────────────────────────────────
    const parallaxImages = document.querySelectorAll('.parallax-img');
    if (parallaxImages.length && !window.matchMedia('(pointer: coarse)').matches) {
        let ticking = false;

        const updateParallax = () => {
            const viewportHeight = window.innerHeight;
            const viewportCenter = viewportHeight / 2;

            parallaxImages.forEach(img => {
                const container = img.parentElement;
                if (!container) return;

                const rect = container.getBoundingClientRect();
                
                // Only animate if the container is visible in the viewport
                if (rect.top < viewportHeight && rect.bottom > 0) {
                    const containerCenter = rect.top + rect.height / 2;
                    const diff = containerCenter - viewportCenter;
                    
                    // Normalize the distance from the center of the viewport
                    const maxDistance = (viewportHeight + rect.height) / 2;
                    const t = Math.max(-1, Math.min(1, diff / maxDistance));
                    
                    // We have 20% extra image height (height is 120%, top is -10%).
                    // This means the safe translation range is within +/- 10% of the container's height.
                    const maxTranslation = rect.height * 0.1;
                    
                    // Compute translation: shift opposite to scroll direction for parallax depth
                    const yPos = -t * maxTranslation;
                    
                    img.style.setProperty('--parallax-y', `${yPos}px`);
                }
            });
        };

        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    updateParallax();
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });

        window.addEventListener('resize', updateParallax);
        updateParallax();
    }
});
