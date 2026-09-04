document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('map-container');
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomLevelDisplay = document.querySelector('.zoom-level');
    
    let scale = 1;
    const minScale = 0.3;
    const maxScale = 5;
    let isDragging = false;
    let startX, startY, translateX = 0, translateY = 0;
    let isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // Создаем модальное окно
    createModal();

    // Загружаем SVG файл карты
    fetch('/static/DZ/images/world_map.svg')
        .then(response => response.text())
        .then(svgData => {
            mapContainer.innerHTML = svgData;
            const svg = mapContainer.querySelector('svg');
            if (svg) {
                if (!svg.getAttribute('viewBox')) {
                    svg.setAttribute('viewBox', '0 0 100 60');
                }
                
                fetch('/DZ/map/zones/')
                    .then(response => response.json())
                    .then(data => {
                        if (data.zones) {
                            addMarkers(svg, data.zones);
                        }
                    })
                    .catch(error => console.error('Ошибка при загрузке данных о зонах:', error));
            }
            
            initMapControls();
        })
        .catch(error => console.error('Ошибка загрузки SVG:', error));

    function createModal() {
        const modal = document.createElement('div');
        modal.id = 'zone-modal';
        modal.className = 'zone-modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="closeZoneModal()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3 id="modal-title"></h3>
                    <button class="modal-close" onclick="closeZoneModal()">×</button>
                </div>
                <div class="modal-body">
                    <div class="modal-actions">
                        <a id="modal-link" href="#" class="modal-btn primary" style="display: none;">Открыть полное досье</a>
                        <button class="modal-btn secondary" onclick="closeZoneModal()">Закрыть</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    function addMarkers(svg, zones) {
        const svgNS = "http://www.w3.org/2000/svg";

        zones.forEach((zone, index) => {
            const marker = document.createElementNS(svgNS, 'circle');
            marker.setAttribute('cx', `${zone.x}%`);
            marker.setAttribute('cy', `${zone.y}%`);
            marker.setAttribute('r', '0.6%');
            marker.setAttribute('class', 'map-marker');
            marker.setAttribute('data-zone-index', index);
            marker.setAttribute('data-zone-name', zone.name);
            marker.setAttribute('data-zone-link', zone.link || '');
            marker.setAttribute('data-zone-description', zone.description || 'Описание отсутствует');

            svg.appendChild(marker);

            const tooltip = createTooltip(zone);
            mapContainer.parentElement.appendChild(tooltip);

            setupMarkerEvents(marker, tooltip, zone);
        });
    }

    function createTooltip(zone) {
        const tooltip = document.createElement('div');
        tooltip.className = 'map-tooltip';
        tooltip.style.cssText = `
            position: absolute;
            display: none;
            padding: 10px 15px;
            background-color: rgba(5, 10, 5, 0.95);
            border: 1px solid var(--main-text);
            border-radius: 6px;
            color: var(--main-text);
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            z-index: 1002;
            pointer-events: none;
            white-space: nowrap;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
            backdrop-filter: blur(2px);
        `;
        tooltip.innerHTML = `<strong>${zone.name}</strong>`;
        return tooltip;
    }

    function setupMarkerEvents(marker, tooltip, zone) {
        // Desktop: hover tooltip + click переход
        marker.addEventListener('mouseenter', (e) => {
            const rect = mapContainer.getBoundingClientRect();
            const x = e.clientX - rect.left + mapContainer.scrollLeft;
            const y = e.clientY - rect.top + mapContainer.scrollTop;
            showTooltip(tooltip, x, y);
        });
        
        marker.addEventListener('mouseleave', () => hideTooltip(tooltip));
        
        // Универсальный click handler
        marker.addEventListener('click', (e) => {
            e.stopPropagation();
            if (isMobile) {
                // Мобильные: показываем модалку
                showZoneModal(zone);
            } else {
                // Desktop: сразу переходим
                const link = zone.link;
                if (link && link !== '#' && link.trim() !== '') {
                    window.location.href = link;
                }
            }
        });
    }

    function showTooltip(tooltip, x, y) {
        tooltip.style.display = 'block';
        requestAnimationFrame(() => {
            const tooltipRect = tooltip.getBoundingClientRect();
            const containerRect = mapContainer.getBoundingClientRect();
            
            let left = x + 20;
            let top = y - tooltipRect.height / 2;
            
            if (left + tooltipRect.width > containerRect.right) {
                left = x - tooltipRect.width - 20;
            }
            if (top < containerRect.top) {
                top = containerRect.top + 10;
            }
            if (top + tooltipRect.height > containerRect.bottom) {
                top = containerRect.bottom - tooltipRect.height - 10;
            }
            
            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${top}px`;
        });
    }

    function hideTooltip(tooltip) {
        tooltip.style.display = 'none';
    }

    // Модальные функции
    window.showZoneModal = function(zone) {
        const modal = document.getElementById('zone-modal');
        const title = document.getElementById('modal-title');
        const link = document.getElementById('modal-link');
        
        title.textContent = zone.name;
        
        if (zone.link && zone.link !== '#' && zone.link.trim() !== '') {
            link.href = zone.link;
            link.style.display = 'inline-block';
        } else {
            link.style.display = 'none';
        }
        
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Блокируем скролл страницы
    };

    window.closeZoneModal = function() {
        const modal = document.getElementById('zone-modal');
        modal.classList.remove('active');
        document.body.style.overflow = '';
    };

    function initMapControls() {
        zoomInBtn.addEventListener('click', () => zoom(1.25));
        zoomOutBtn.addEventListener('click', () => zoom(0.8));
        
        // Drag & Pan
        let dragStart = null;
        let initialTranslate = { x: 0, y: 0 };
        
        mapContainer.addEventListener('mousedown', (e) => {
            if (e.button === 0 && !isMobile) {
                dragStart = { x: e.clientX, y: e.clientY };
                initialTranslate = { x: translateX, y: translateY };
                document.body.style.userSelect = 'none';
                mapContainer.style.cursor = 'grabbing';
            }
        });
        
        document.addEventListener('mousemove', (e) => {
            if (dragStart) {
                const dx = e.clientX - dragStart.x;
                const dy = e.clientY - dragStart.y;
                translateX = initialTranslate.x + dx;
                translateY = initialTranslate.y + dy;
                applyTransform();
            }
        });
        
        document.addEventListener('mouseup', () => {
            dragStart = null;
            mapContainer.style.cursor = 'grab';
            document.body.style.userSelect = '';
        });

        // Touch события (работают на всех устройствах)
        let touchStart = null;
        let initialPinchDistance = 0;
        
        mapContainer.addEventListener('touchstart', (e) => {
            e.stopPropagation();
            if (e.touches.length === 1) {
                touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
                initialTranslate = { x: translateX, y: translateY };
            } else if (e.touches.length === 2) {
                initialPinchDistance = getTouchDistance(e.touches);
            }
        }, { passive: false });
        
        mapContainer.addEventListener('touchmove', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (e.touches.length === 1 && touchStart) {
                const dx = e.touches[0].clientX - touchStart.x;
                const dy = e.touches[0].clientY - touchStart.y;
                translateX = initialTranslate.x + dx;
                translateY = initialTranslate.y + dy;
                applyTransform();
            } else if (e.touches.length === 2 && initialPinchDistance > 0) {
                const currentDistance = getTouchDistance(e.touches);
                const factor = currentDistance / initialPinchDistance;
                zoom(factor);
                initialPinchDistance = currentDistance;
            }
        }, { passive: false });
        
        mapContainer.addEventListener('touchend', (e) => {
            touchStart = null;
            initialPinchDistance = 0;
        });

        // Закрытие модалки по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeZoneModal();
            }
        });

        updateZoomDisplay();
    }

    // Остальные функции без изменений...
    function zoom(factor, clientX = null, clientY = null) {
        const newScale = Math.max(minScale, Math.min(maxScale, scale * factor));
        if (Math.abs(newScale - scale) < 0.01) return;

        if (clientX && clientY) {
            const rect = mapContainer.getBoundingClientRect();
            const x = (clientX - rect.left - translateX) / scale;
            const y = (clientY - rect.top - translateY) / scale;
            
            translateX = clientX - rect.left - x * newScale;
            translateY = clientY - rect.top - y * newScale;
        }

        scale = newScale;
        applyTransform();
        updateZoomDisplay();
    }

    function applyTransform() {
        mapContainer.style.transform = `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
    }

    function updateZoomDisplay() {
        zoomLevelDisplay.textContent = `${Math.round(scale * 100)}%`;
    }

    function getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
});