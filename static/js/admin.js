document.addEventListener('DOMContentLoaded', () => {
    // Session countdown timer (30 min)
    const timerEl = document.getElementById('timer-display');
    if (timerEl) {
        let remaining = 30 * 60;
        const updateTimer = () => {
            const m = Math.floor(remaining / 60).toString().padStart(2, '0');
            const s = (remaining % 60).toString().padStart(2, '0');
            timerEl.textContent = `${m}:${s}`;
            if (remaining <= 300) timerEl.style.color = '#ff9800';
            if (remaining <= 60) timerEl.style.color = '#ff4a4a';
            if (remaining <= 0) { window.location.href = '/admin/logout'; return; }
            remaining--;
        };
        updateTimer();
        setInterval(updateTimer, 1000);

        // Reset timer on any interaction
        ['click', 'keydown', 'mousemove'].forEach(evt => {
            document.addEventListener(evt, () => { remaining = 30 * 60; });
        });
    }
});
