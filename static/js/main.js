// main.js — Core page behaviours
document.addEventListener('DOMContentLoaded', () => {

    // ── Dark Mode (load from storage) ──────────────────────
    const savedTheme = localStorage.getItem('theme') || 'dark';
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
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    const scrolled = window.pageYOffset;
                    parallaxImages.forEach(img => {
                        const speed = 0.4;
                        const yPos = -(scrolled * speed);
                        // Limit parallax translation to not break layout boundaries
                        const limitedY = Math.max(-100, Math.min(100, yPos));
                        img.style.transform = `translateY(${limitedY}px)`;
                    });
                    ticking = false;
                });
                ticking = true;
            }
        });
    }
});
