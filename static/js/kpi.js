// KPI main page JavaScript
console.log('KPI main page loaded');

// Add hover effects and animations
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.kpi-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });
});

