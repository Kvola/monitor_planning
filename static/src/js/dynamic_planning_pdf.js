/**
 * JavaScript pour le calendrier des planifications de moniteurs
 * Améliore l'interactivité et l'expérience utilisateur
 */

class MonitorPlanningCalendar {
    constructor() {
        this.currentDate = new Date();
        this.isLoading = false;
        this.selectedFilters = {
            status: '',
            monitor_id: '',
            school_id: ''
        };
        
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.setupAccessibility();
        this.setupKeyboardNavigation();
        this.loadSavedFilters();
    }

    /**
     * Attacher les event listeners
     */
    attachEventListeners() {
        // Navigation du calendrier
        document.addEventListener('click', (e) => {
            if (e.target.matches('.calendar-day') || e.target.closest('.calendar-day')) {
                const calendarDay = e.target.matches('.calendar-day') ? e.target : e.target.closest('.calendar-day');
                this.handleDayClick(calendarDay);
            }
            
            if (e.target.matches('.planning-item') || e.target.closest('.planning-item')) {
                e.stopPropagation();
                const planningItem = e.target.matches('.planning-item') ? e.target : e.target.closest('.planning-item');
                this.handlePlanningClick(planningItem);
            }
        });

        // Filtres
        const filterForm = document.querySelector('form[method="get"]');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                this.handleFilterSubmit(e);
            });
        }

        // Auto-sauvegarde des filtres
        const filterSelects = document.querySelectorAll('select[name="status"], select[name="monitor_id"], select[name="school_id"]');
        filterSelects.forEach(select => {
            select.addEventListener('change', () => {
                this.saveFilters();
            });
        });

        // Raccourcis clavier globaux
        document.addEventListener('keydown', (e) => {
            this.handleGlobalKeydown(e);
        });
    }

    /**
     * Gérer le clic sur un jour
     */
    handleDayClick(dayElement) {
        const date = dayElement.getAttribute('data-date');
        if (!date) return;

        // Effet visuel
        dayElement.classList.add('clicked');
        setTimeout(() => dayElement.classList.remove('clicked'), 150);

        // Navigation
        try {
            window.location.href = `/monitor/planning/day/${date}`;
        } catch (error) {
            console.warn('Vue détaillée du jour non disponible:', error);
            this.showNotification('Vue détaillée non disponible', 'warning');
        }
    }

    /**
     * Gérer le clic sur une planification
     */
    handlePlanningClick(planningItem) {
        const planningId = planningItem.getAttribute('data-planning-id');
        if (!planningId) return;

        // Effet visuel
        planningItem.classList.add('clicked');
        setTimeout(() => planningItem.classList.remove('clicked'), 150);

        // Navigation vers les détails
        window.location.href = `/monitor/planning/${planningId}`;
    }

    /**
     * Gérer la soumission des filtres
     */
    handleFilterSubmit(e) {
        this.showLoading(true);
        this.saveFilters();
    }

    /**
     * Configuration de l'accessibilité
     */
    setupAccessibility() {
        // Ajouter les attributs ARIA et les gestionnaires d'événements pour l'accessibilité
        document.querySelectorAll('.calendar-day').forEach(cell => {
            cell.setAttribute('role', 'button');
            cell.setAttribute('tabindex', '0');
            cell.setAttribute('aria-label', this.generateDayAriaLabel(cell));
            
            // Gestion du focus
            cell.addEventListener('focus', () => {
                this.handleDayFocus(cell);
            });
            
            cell.addEventListener('blur', () => {
                this.handleDayBlur(cell);
            });
        });

        // Ajouter les labels pour les planifications
        document.querySelectorAll('.planning-item').forEach(item => {
            item.setAttribute('role', 'button');
            item.setAttribute('tabindex', '0');
            item.setAttribute('aria-label', this.generatePlanningAriaLabel(item));
        });
    }

    /**
     * Configuration de la navigation au clavier
     */
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            const focusedElement = document.activeElement;
            
            if (focusedElement && focusedElement.classList.contains('calendar-day')) {
                this.handleCalendarKeyNavigation(e, focusedElement);
            }
            
            if (focusedElement && focusedElement.classList.contains('planning-item')) {
                this.handlePlanningKeyNavigation(e, focusedElement);
            }
        });
    }

    /**
     * Navigation au clavier dans le calendrier
     */
    handleCalendarKeyNavigation(e, currentCell) {
        const cells = Array.from(document.querySelectorAll('.calendar-day'));
        const currentIndex = cells.indexOf(currentCell);
        let targetIndex = currentIndex;

        switch(e.key) {
            case 'ArrowRight':
                targetIndex = Math.min(currentIndex + 1, cells.length - 1);
                break;
            case 'ArrowLeft':
                targetIndex = Math.max(currentIndex - 1, 0);
                break;
            case 'ArrowDown':
                targetIndex = Math.min(currentIndex + 7, cells.length - 1);
                break;
            case 'ArrowUp':
                targetIndex = Math.max(currentIndex - 7, 0);
                break;
            case 'Enter':
            case ' ':
                e.preventDefault();
                this.handleDayClick(currentCell);
                return;
            case 'Home':
                targetIndex = 0;
                break;
            case 'End':
                targetIndex = cells.length - 1;
                break;
            default:
                return;
        }

        e.preventDefault();
        if (cells[targetIndex]) {
            cells[targetIndex].focus();
        }
    }

    /**
     * Navigation au clavier pour les planifications
     */
    handlePlanningKeyNavigation(e, currentItem) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.handlePlanningClick(currentItem);
        }
    }

    /**
     * Gérer les raccourcis clavier globaux
     */
    handleGlobalKeydown(e) {
        // Ctrl/Cmd + F pour focus sur les filtres
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const firstFilter = document.querySelector('select[name="status"]');
            if (firstFilter) firstFilter.focus();
        }

        // Échap pour nettoyer les filtres
        if (e.key === 'Escape') {
            this.resetFilters();
        }

        // Flèches gauche/droite pour navigation mensuelle
        if (e.altKey) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.navigateMonth(-1);
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.navigateMonth(1);
            }
        }
    }

    /**
     * Générer le label ARIA pour un jour
     */
    generateDayAriaLabel(dayCell) {
        const date = dayCell.getAttribute('data-date');
        const plannings = dayCell.querySelectorAll('.planning-item');
        const planningCount = plannings.length;
        
        let label = `${date}`;
        if (planningCount > 0) {
            label += `, ${planningCount} planification${planningCount > 1 ? 's' : ''}`;
        } else {
            label += ', aucune planification';
        }
        
        if (dayCell.classList.contains('today-highlight')) {
            label += ', aujourd\'hui';
        }
        
        return label;
    }

    /**
     * Générer le label ARIA pour une planification
     */
    generatePlanningAriaLabel(planningItem) {
        const title = planningItem.getAttribute('title') || '';
        const time = planningItem.querySelector('.fw-bold')?.textContent || '';
        const monitor = planningItem.querySelector('.text-truncate')?.textContent || '';
        
        return `Planification ${time ? 'à ' + time : ''} avec ${monitor}. ${title}`;
    }

    /**
     * Gérer le focus sur un jour
     */
    handleDayFocus(dayCell) {
        // Afficher un tooltip avec les informations
        this.showDayTooltip(dayCell);
    }

    /**
     * Gérer la perte de focus sur un jour
     */
    handleDayBlur(dayCell) {
        // Masquer le tooltip
        this.hideDayTooltip(dayCell);
    }

    /**
     * Afficher un tooltip pour un jour
     */
    showDayTooltip(dayCell) {
        const existingTooltip = document.querySelector('.day-tooltip');
        if (existingTooltip) existingTooltip.remove();

        const plannings = dayCell.querySelectorAll('.planning-item');
        if (plannings.length === 0) return;

        const tooltip = document.createElement('div');
        tooltip.className = 'day-tooltip position-absolute bg-dark text-white p-2 rounded shadow';
        tooltip.style.zIndex = '1000';
        tooltip.style.fontSize = '0.8rem';
        tooltip.style.maxWidth = '200px';

        let content = `<strong>${plannings.length} planification${plannings.length > 1 ? 's' : ''}</strong><br>`;
        plannings.forEach((planning, index) => {
            if (index < 3) { // Limiter à 3 pour éviter un tooltip trop grand
                const title = planning.getAttribute('title') || '';
                content += `• ${title}<br>`;
            }
        });
        
        if (plannings.length > 3) {
            content += `• ... et ${plannings.length - 3} autre${plannings.length - 3 > 1 ? 's' : ''}`;
        }

        tooltip.innerHTML = content;
        
        // Positionner le tooltip
        const rect = dayCell.getBoundingClientRect();
        tooltip.style.left = (rect.left + rect.width / 2) + 'px';
        tooltip.style.top = (rect.bottom + window.scrollY + 5) + 'px';
        tooltip.style.transform = 'translateX(-50%)';

        document.body.appendChild(tooltip);
    }

    /**
     * Masquer le tooltip d'un jour
     */
    hideDayTooltip(dayCell) {
        const tooltip = document.querySelector('.day-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }

    /**
     * Naviguer d'un mois
     */
    navigateMonth(direction) {
        const currentYear = parseInt(document.querySelector('input[name="year"]')?.value || new Date().getFullYear());
        const currentMonth = parseInt(document.querySelector('input[name="month"]')?.value || new Date().getMonth() + 1);
        
        let newMonth = currentMonth + direction;
        let newYear = currentYear;
        
        if (newMonth > 12) {
            newMonth = 1;
            newYear++;
        } else if (newMonth < 1) {
            newMonth = 12;
            newYear--;
        }
        
        // Conserver les filtres actuels
        const params = new URLSearchParams(window.location.search);
        params.set('year', newYear);
        params.set('month', newMonth);
        
        window.location.href = `/monitor/planning/calendar?${params.toString()}`;
    }

    /**
     * Sauvegarder les filtres dans le localStorage
     */
    saveFilters() {
        const filters = {
            status: document.querySelector('select[name="status"]')?.value || '',
            monitor_id: document.querySelector('select[name="monitor_id"]')?.value || '',
            school_id: document.querySelector('select[name="school_id"]')?.value || ''
        };
        
        localStorage.setItem('monitor_planning_filters', JSON.stringify(filters));
    }

    /**
     * Charger les filtres sauvegardés
     */
    loadSavedFilters() {
        try {
            const savedFilters = localStorage.getItem('monitor_planning_filters');
            if (savedFilters) {
                const filters = JSON.parse(savedFilters);
                
                // Appliquer les filtres uniquement s'ils ne sont pas déjà définis dans l'URL
                const urlParams = new URLSearchParams(window.location.search);
                
                Object.keys(filters).forEach(key => {
                    if (!urlParams.has(key) && filters[key]) {
                        const select = document.querySelector(`select[name="${key}"]`);
                        if (select) {
                            select.value = filters[key];
                        }
                    }
                });
            }
        } catch (error) {
            console.warn('Erreur lors du chargement des filtres sauvegardés:', error);
        }
    }

    /**
     * Réinitialiser les filtres
     */
    resetFilters() {
        const selects = document.querySelectorAll('select[name="status"], select[name="monitor_id"], select[name="school_id"]');
        selects.forEach(select => select.value = '');
        
        localStorage.removeItem('monitor_planning_filters');
        
        // Rediriger sans les paramètres de filtre
        const url = new URL(window.location);
        url.search = `year=${url.searchParams.get('year') || new Date().getFullYear()}&month=${url.searchParams.get('month') || new Date().getMonth() + 1}`;
        window.location.href = url.toString();
    }

    /**
     * Afficher l'état de chargement
     */
    showLoading(show = true) {
        const calendar = document.querySelector('.calendar-table');
        if (!calendar) return;

        if (show) {
            calendar.classList.add('calendar-loading');
            this.isLoading = true;
        } else {
            calendar.classList.remove('calendar-loading');
            this.isLoading = false;
        }
    }

    /**
     * Afficher une notification
     */
    showNotification(message, type = 'info') {
        // Supprimer les notifications existantes
        const existingNotifications = document.querySelectorAll('.calendar-notification');
        existingNotifications.forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `calendar-notification alert alert-${type} position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 1050;
            max-width: 300px;
            animation: slideInRight 0.3s ease;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Auto-suppression après 3 secondes
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Initialiser les animations CSS
     */
    initAnimations() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            .clicked {
                transform: scale(0.95);
                transition: transform 0.1s ease;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Améliorer l'expérience mobile
     */
    setupMobileOptimizations() {
        // Détecter les appareils tactiles
        if ('ontouchstart' in window) {
            document.body.classList.add('touch-device');
            
            // Améliorer les interactions tactiles
            document.addEventListener('touchstart', (e) => {
                if (e.target.matches('.planning-item')) {
                    e.target.classList.add('touch-active');
                }
            });
            
            document.addEventListener('touchend', (e) => {
                if (e.target.matches('.planning-item')) {
                    setTimeout(() => {
                        e.target.classList.remove('touch-active');
                    }, 150);
                }
            });
        }
    }
}

// Styles additionnels pour les interactions
const additionalStyles = `
    .touch-device .planning-item {
        min-height: 32px;
        display: flex;
        align-items: center;
    }
    
    .touch-active {
        background-color: rgba(0,0,0,0.1) !important;
    }
    
    .day-tooltip {
        pointer-events: none;
        animation: fadeInTooltip 0.2s ease;
    }
    
    @keyframes fadeInTooltip {
        from { opacity: 0; transform: translateX(-50%) translateY(-5px); }
        to { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
`;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    // Ajouter les styles additionnels
    const styleSheet = document.createElement('style');
    styleSheet.textContent = additionalStyles;
    document.head.appendChild(styleSheet);
    
    // Initialiser le calendrier
    window.monitorPlanningCalendar = new MonitorPlanningCalendar();
    window.monitorPlanningCalendar.initAnimations();
    window.monitorPlanningCalendar.setupMobileOptimizations();
});

// Fonctions globales pour compatibilité avec le template
window.openDayModal = function(date) {
    if (window.monitorPlanningCalendar) {
        const dayElement = document.querySelector(`[data-date="${date}"]`);
        if (dayElement) {
            window.monitorPlanningCalendar.handleDayClick(dayElement);
        }
    }
};

window.openPlanningDetails = function(planningId) {
    if (window.monitorPlanningCalendar) {
        const planningElement = document.querySelector(`[data-planning-id="${planningId}"]`);
        if (planningElement) {
            window.monitorPlanningCalendar.handlePlanningClick(planningElement);
        }
    }
};

window.resetFilters = function() {
    if (window.monitorPlanningCalendar) {
        window.monitorPlanningCalendar.resetFilters();
    }
};