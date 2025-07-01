// static/js/main.js

// Configuration object for easy maintenance
const CONFIG = {
    MAP: {
        DEFAULT_CENTER: [54.5, -2], // UK center
        DEFAULT_ZOOM: 6,
        TILE_LAYER: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        ATTRIBUTION: '© OpenStreetMap contributors'
    },
    API: {
        DEBOUNCE_DELAY: 300,
        TIMEOUT: 10000
    },
    UI: {
        MAX_SUGGESTIONS: 10,
        ANIMATION_DURATION: 300
    }
};

// State management
const AppState = {
    map: null,
    markers: [],
    startPointMarker: null,
    distanceCircleManager: null,
    isLoading: false,
    currentSearch: null,
    currentTab: null,
    tabButtons: null,
    debouncedFunctions: new Set() // Track debounced functions for cleanup
};

// Utility functions
const Utils = {
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    showLoading(show = true) {
        const button = document.getElementById('searchButton');
        const buttonText = document.getElementById('searchButtonText');
        const buttonSpinner = document.getElementById('searchButtonSpinner');
        
        AppState.isLoading = show;
        
        if (show) {
            button.classList.add('loading');
            buttonText.textContent = 'Searching...';
            buttonSpinner.style.display = 'inline-block';
        } else {
            button.classList.remove('loading');
            buttonText.textContent = 'Find Destinations';
            buttonSpinner.style.display = 'none';
        }
    },

    showError(message, containerId = 'results') {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const errorDiv = Utils.createElement('div', 'error-message');
        const icon = Utils.createElement('i', 'fas fa-exclamation-triangle mr-2');
        const text = document.createTextNode(message);
        
        errorDiv.appendChild(icon);
        errorDiv.appendChild(text);
        container.appendChild(errorDiv);
    },

    clearResults() {
        const resultsDiv = document.getElementById('results');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
        
        // Clean up scroll to top button
        if (AppState.scrollToTopBtn) {
            AppState.scrollToTopBtn.remove();
            AppState.scrollToTopBtn = null;
        }
        
        // Remove old markers
        AppState.markers.forEach(marker => {
            if (AppState.map && AppState.map.hasLayer(marker)) {
                AppState.map.removeLayer(marker);
            }
        });
        AppState.markers = [];
    },
    
    // Safe DOM element creation with error handling
    createElement(tag, className, innerHTML = '') {
        try {
            const element = document.createElement(tag);
            if (className) {
                element.className = className;
            }
            if (innerHTML) {
                element.innerHTML = innerHTML;
            }
            return element;
        } catch (error) {
            console.error('Error creating element:', error);
            return null;
        }
    },
    
    // Safe element querying with error handling
    getElement(id) {
        try {
            return document.getElementById(id);
        } catch (error) {
            console.error(`Error getting element with id '${id}':`, error);
            return null;
        }
    }
};

// Initialize the map
function initializeMap() {
    AppState.map = L.map('map', {
        zoomControl: false
    }).setView(CONFIG.MAP.DEFAULT_CENTER, CONFIG.MAP.DEFAULT_ZOOM);

    L.tileLayer(CONFIG.MAP.TILE_LAYER, {
        attribution: CONFIG.MAP.ATTRIBUTION
    }).addTo(AppState.map);

    // Initialize distance circle manager
    AppState.distanceCircleManager = new DistanceCircleManager(AppState.map);
}

// Set up smart date selector for next 7 days
function setupDateSelector() {
    const dateInput = document.getElementById('date');
    const dateSelector = document.getElementById('dateSelector');
    const today = new Date();
    
    // Clear existing options
    dateSelector.innerHTML = '';
    
    // Create top row (3 dates)
    const topRow = document.createElement('div');
    topRow.className = 'date-row top';
    
    // Create bottom row (4 dates)
    const bottomRow = document.createElement('div');
    bottomRow.className = 'date-row';
    
    // Create options for next 7 days
    for (let i = 0; i < 7; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const dayName = dayNames[date.getDay()];
        const dayDate = date.getDate();
        const month = date.getMonth() + 1;
        const year = date.getFullYear();
        const dateString = `${year}-${month.toString().padStart(2, '0')}-${dayDate.toString().padStart(2, '0')}`;
        
        const dateOption = document.createElement('div');
        dateOption.className = 'date-option';
        if (i === 0) {
            dateOption.classList.add('selected');
            dateInput.value = dateString;
        }
        dateOption.innerHTML = `
            <span class="day-name">${dayName}</span>
            <span class="day-date">${dayDate}</span>
        `;
        
        dateOption.addEventListener('click', () => {
            // Remove selected class from all options
            document.querySelectorAll('.date-option').forEach(opt => opt.classList.remove('selected'));
            // Add selected class to clicked option
            dateOption.classList.add('selected');
            // Update hidden input
            dateInput.value = dateString;
        });
        
        // Add to appropriate row (first 3 to top, last 4 to bottom)
        if (i < 3) {
            topRow.appendChild(dateOption);
        } else {
            bottomRow.appendChild(dateOption);
        }
    }
    
    dateSelector.appendChild(topRow);
    dateSelector.appendChild(bottomRow);
}

// Create custom icon class
const WeatherIcon = L.Icon.extend({
    options: {
        iconSize: [40, 40],
        iconAnchor: [20, 20],
        popupAnchor: [0, -20]
    }
});

// Distance circle management
class DistanceCircleManager {
    constructor(map) {
        this.map = map;
        this.circle = null;
        this.center = null;
        this.radius = 200; // miles
        this.handleMarker = null;
        this.isDragging = false;
        this.init();
    }

    init() {
        // No DOM controls needed
        this.setupMapEvents();
    }

    setupMapEvents() {
        this.map.on('zoom move resize', () => this.updateHandlePosition());
    }

    setCenter(lat, lng) {
        this.center = { lat, lng };
        this.updateCircle();
        this.updateHandlePosition();
    }

    setRadius(radius) {
        this.radius = radius;
        this.updateCircle();
        this.updateHandlePosition();
        this.updateFormSlider();
    }

    updateCircle() {
        if (!this.center) return;
        if (this.circle) this.map.removeLayer(this.circle);
        this.circle = L.circle([this.center.lat, this.center.lng], {
            radius: this.radius * 1609.34,
            color: '#3B82F6',
            fillColor: '#93C5FD',
            fillOpacity: 0.2,
            weight: 2
        }).addTo(this.map);
    }

    updateHandlePosition() {
        if (!this.center) return;
        // Calculate the LatLng for the handle at the edge of the circle (3 o'clock, 90 degrees)
        const angleRad = Math.PI / 2; // 3 o'clock position (90 degrees)
        const earthRadius = 6378137; // meters
        const d = this.radius * 1609.34; // meters
        const lat1 = this.center.lat * Math.PI / 180;
        const lng1 = this.center.lng * Math.PI / 180;
        const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d / earthRadius) + Math.cos(lat1) * Math.sin(d / earthRadius) * Math.cos(angleRad));
        const lng2 = lng1 + Math.atan2(Math.sin(angleRad) * Math.sin(d / earthRadius) * Math.cos(lat1), Math.cos(d / earthRadius) - Math.sin(lat1) * Math.sin(lat2));
        const handleLat = lat2 * 180 / Math.PI;
        const handleLng = lng2 * 180 / Math.PI;

        // Create or move the handle marker
        if (!this.handleMarker) {
            this.handleMarker = L.marker([handleLat, handleLng], {
                draggable: true,
                icon: L.divIcon({
                    className: 'distance-handle-marker',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15],
                    html: '<div class="distance-control-handle"></div>'
                })
            }).addTo(this.map);
            this.handleMarker.on('drag', (e) => this.onHandleDrag(e));
        } else {
            this.handleMarker.setLatLng([handleLat, handleLng]);
        }

        // Update or add tooltip
        if (!this.handleMarker.getTooltip()) {
            this.handleMarker.bindTooltip(
                () => `${this.radius} miles`,
                { permanent: true, direction: 'right', className: 'distance-label-tooltip' }
            ).openTooltip();
        } else {
            this.handleMarker.setTooltipContent(`${this.radius} miles`);
        }
    }

    onHandleDrag(e) {
        if (!this.center) return;
        const handleLatLng = e.target.getLatLng();
        const centerLatLng = L.latLng(this.center.lat, this.center.lng);
        const meters = centerLatLng.distanceTo(handleLatLng);
        const miles = Math.round(meters / 1609.34);
        this.setRadius(Math.max(1, Math.min(200, miles)));
    }

    updateFormSlider() {
        const slider = document.getElementById('distance');
        const valueDisplay = document.getElementById('distanceValue');
        if (slider) slider.value = this.radius;
        if (valueDisplay) valueDisplay.textContent = this.radius;
    }

    hide() {
        if (this.circle) this.map.removeLayer(this.circle);
        if (this.handleMarker) this.map.removeLayer(this.handleMarker);
    }

    destroy() {
        this.hide();
        this.map.off('zoom move resize');
    }
}

// Update distance value display and map radius
function updateDistance(value) {
    if (AppState.distanceCircleManager) {
        AppState.distanceCircleManager.setRadius(parseInt(value));
    }
}

// Update distance control position after map changes
function updateDistanceControl() {
    if (AppState.distanceCircleManager) {
        AppState.distanceCircleManager.updateHandlePosition();
    }
}

// Location autocomplete functionality
function setupLocationAutocomplete() {
    const fromInput = document.getElementById('from');
    const suggestionsDiv = document.getElementById('locationSuggestions');
    
    const debouncedSearch = Utils.debounce(async (query) => {
        if (query.length < 2) {
            suggestionsDiv.innerHTML = '';
            suggestionsDiv.style.display = 'none';
            return;
        }
        
        try {
            const response = await fetch(`/location-suggest?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();
            
            if (suggestions.length === 0) {
                suggestionsDiv.innerHTML = '';
                suggestionsDiv.style.display = 'none';
                return;
            }
            
            suggestionsDiv.innerHTML = suggestions.map(suggestion => `
                <div class="suggestion-item" data-lat="${suggestion.lat}" data-lon="${suggestion.lon}">
                    ${suggestion.display_name}
                </div>
            `).join('');
            
            suggestionsDiv.style.display = 'block';
            
            // Add click handlers
            suggestionsDiv.querySelectorAll('.suggestion-item').forEach(item => {
                item.addEventListener('click', () => {
                    fromInput.value = item.textContent.trim();
                    suggestionsDiv.style.display = 'none';
                    
                    const lat = parseFloat(item.dataset.lat);
                    const lon = parseFloat(item.dataset.lon);
                    updateMapLocation({ lat, lon });
                });
            });
            
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }, CONFIG.API.DEBOUNCE_DELAY);
    
    // Store the debounced function for cleanup
    fromInput._debouncedSearch = debouncedSearch;
    
    fromInput.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
    });
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (!fromInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
            suggestionsDiv.style.display = 'none';
        }
    });
}

function updateMapLocation(coordinates) {
    // Remove existing start point marker
    if (AppState.startPointMarker) {
        AppState.map.removeLayer(AppState.startPointMarker);
    }

    // Create start point marker
    const startIcon = L.divIcon({
        className: 'start-point-marker',
        html: '<div style="background-color: #3B82F6; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });

    AppState.startPointMarker = L.marker([coordinates.lat, coordinates.lon], {
        icon: startIcon
    }).addTo(AppState.map);

    // Update distance circle center
    if (AppState.distanceCircleManager) {
        AppState.distanceCircleManager.setCenter(coordinates.lat, coordinates.lon);
    }

    AppState.map.setView([coordinates.lat, coordinates.lon], 8);
}

// Handle form submission
function setupFormSubmission() {
    const searchForm = document.getElementById('searchForm');
    const distanceSlider = document.getElementById('distance');

    // Update distance on slider change
    distanceSlider.addEventListener('input', (e) => {
        updateDistance(e.target.value);
    });

    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (AppState.isLoading) return; // Prevent multiple submissions
        
        const formData = {
            from: document.getElementById('from').value,
            date: document.getElementById('date').value,
            start_hour: document.getElementById('start-hour').value,
            end_hour: document.getElementById('end-hour').value,
            distance: distanceSlider.value
        };

        // Store current search for potential cancellation
        AppState.currentSearch = formData;

        try {
            Utils.showLoading(true);
            Utils.clearResults();

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.API.TIMEOUT);

            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (!data.sunny_destinations || data.sunny_destinations.length === 0) {
                const resultsDiv = document.getElementById('results');
                if (resultsDiv) {
                    resultsDiv.innerHTML = '<p class="text-center text-gray-500">No destinations found within your criteria.</p>';
                }
                return;
            }

            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            if (error.name === 'AbortError') {
                Utils.showError('Request timed out. Please try again.');
            } else {
                Utils.showError('An error occurred while searching for destinations. Please try again.');
            }
        } finally {
            Utils.showLoading(false);
            AppState.currentSearch = null;
        }
    });
}

// Display search results with tabs
function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    if (!resultsDiv) return;
    
    // Validate data
    if (!data.sunny_destinations || !data.comfortable_destinations) {
        Utils.showError('Invalid data received from server');
        return;
    }
    
    // Create tabs container
    const tabsContainer = document.createElement('div');
    tabsContainer.className = 'mb-6';
    
    // Create tab buttons
    const tabButtons = document.createElement('div');
    tabButtons.className = 'flex border-b border-gray-200 mb-4';
    
    const sunnyTab = document.createElement('button');
    sunnyTab.className = 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600 bg-white';
    sunnyTab.textContent = `Sunny Destinations (${data.sunny_destinations.length})`;
    sunnyTab.onclick = () => switchTab('sunny', data);
    
    const comfortTab = document.createElement('button');
    comfortTab.className = 'px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 hover:border-gray-300';
    comfortTab.textContent = `Comfortable Destinations (${data.comfortable_destinations.length})`;
    comfortTab.onclick = () => switchTab('comfort', data);
    
    tabButtons.appendChild(sunnyTab);
    tabButtons.appendChild(comfortTab);
    tabsContainer.appendChild(tabButtons);
    
    // Create content container
    const contentContainer = document.createElement('div');
    contentContainer.id = 'tab-content';
    tabsContainer.appendChild(contentContainer);
    
    resultsDiv.appendChild(tabsContainer);
    
    // Show sunny destinations by default
    displaySunnyDestinations(data.sunny_destinations);
    
    // Store tab state
    AppState.currentTab = 'sunny';
    AppState.tabButtons = { sunny: sunnyTab, comfort: comfortTab };

    if (AppState.distanceCircleManager && AppState.distanceCircleManager.center) {
        AppState.distanceCircleManager.show();
    }
}

function switchTab(tabName, data) {
    // Update tab button styles
    Object.values(AppState.tabButtons).forEach(btn => {
        btn.className = 'px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 hover:border-gray-300';
    });
    
    AppState.tabButtons[tabName].className = 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600 bg-white';
    
    // Clear existing markers
    AppState.markers.forEach(marker => {
        if (AppState.map.hasLayer(marker)) {
            AppState.map.removeLayer(marker);
        }
    });
    AppState.markers = [];
    
    // Display appropriate destinations
    if (tabName === 'sunny') {
        displaySunnyDestinations(data.sunny_destinations);
    } else {
        displayComfortableDestinations(data.comfortable_destinations);
    }
    
    AppState.currentTab = tabName;

    if (AppState.distanceCircleManager && AppState.distanceCircleManager.center) {
        AppState.distanceCircleManager.show();
    }
}

function displaySunnyDestinations(destinations) {
    displayDestinations(destinations, 'sunny');
}

function displayComfortableDestinations(destinations) {
    displayDestinations(destinations, 'comfort');
}

function displayDestinations(destinations, type) {
    const contentContainer = document.getElementById('tab-content');
    if (!contentContainer) return;
    
    contentContainer.innerHTML = '';
    
    // Add results counter
    const resultsCounter = document.createElement('div');
    resultsCounter.className = 'mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200';
    resultsCounter.innerHTML = `
        <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-blue-800">
                Showing ${destinations.length} destinations
            </span>
            <span class="text-xs text-blue-600">
                Click any destination to center the map
            </span>
        </div>
    `;
    contentContainer.appendChild(resultsCounter);
    
    const config = {
        sunny: {
            icon: 'fas fa-sun',
            iconColor: 'text-yellow-500',
            scoreClass: 'sunny-score-circle',
            markerClass: 'sunny-marker-icon',
            scoreKey: 'sunny_score',
            levelKey: 'sunny_level',
            gradient: 'from-yellow-400 to-orange-500',
            textColor: 'text-yellow-600',
            label: 'Sunny Score'
        },
        comfort: {
            icon: 'fas fa-thermometer-half',
            iconColor: 'text-green-500',
            scoreClass: 'comfort-score-circle',
            markerClass: 'comfort-marker-icon',
            scoreKey: 'comfort_score',
            levelKey: 'comfort_level',
            gradient: 'from-green-400 to-blue-500',
            textColor: 'text-green-600',
            label: 'Comfort Score'
        }
    };
    
    const typeConfig = config[type];
    
    destinations.forEach((destination, idx) => {
        // Create result card
        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg shadow-md p-3 hover:shadow-lg transition-shadow mb-2 cursor-pointer';
        card.innerHTML = `
            <div class="result-card-content">
                <div class="result-card-info">
                    <h3 class="font-bold text-lg">${destination.city}</h3>
                    <p class="text-gray-600">${destination.region}, ${destination.country}</p>
                    <p class="text-gray-500">${Math.round(destination.distance)} miles away</p>
                    <div class="${typeConfig.scoreClass.replace('-circle', '')}-info mt-2">
                        <div class="flex items-center">
                            <i class="${typeConfig.icon} ${typeConfig.iconColor} mr-2"></i>
                            <span class="font-semibold text-lg">${destination[typeConfig.scoreKey]}/10</span>
                            <span class="ml-2 text-sm text-gray-600">(${destination[typeConfig.levelKey]})</span>
                        </div>
                    </div>
                </div>
                <div class="flex flex-col items-center justify-center">
                    <div class="${typeConfig.scoreClass} mb-2">
                        <div class="w-16 h-16 rounded-full bg-gradient-to-br ${typeConfig.gradient} flex items-center justify-center text-white font-bold text-lg">
                            ${destination[typeConfig.scoreKey]}
                        </div>
                    </div>
                    <p class="text-sm text-gray-600">${typeConfig.label}</p>
                </div>
            </div>
        `;
        contentContainer.appendChild(card);

        // Create custom icon for the marker
        const markerIcon = L.divIcon({
            className: typeConfig.markerClass,
            html: `
                <div class="w-10 h-10 rounded-full bg-gradient-to-br ${typeConfig.gradient} flex items-center justify-center text-white font-bold text-xs border-2 border-white shadow-lg">
                    ${destination[typeConfig.scoreKey]}
                </div>
            `,
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });

        // Create marker with custom icon
        const marker = L.marker([destination.coordinates.lat, destination.coordinates.lon], {
            icon: markerIcon
        })
        .addTo(AppState.map)
        .bindPopup(`
            <div class="text-center">
                <div class="${typeConfig.scoreClass} inline-block mb-2">
                    <div class="w-12 h-12 rounded-full bg-gradient-to-br ${typeConfig.gradient} flex items-center justify-center text-white font-bold text-sm">
                        ${destination[typeConfig.scoreKey]}
                    </div>
                </div>
                <strong>${destination.city}</strong><br>
                ${destination.region}, ${destination.country}<br>
                <span class="${typeConfig.textColor} font-semibold">${destination[typeConfig.levelKey]}</span><br>
                ${destination.distance} miles away
            </div>
        `);
        AppState.markers.push(marker);

        // Add click event to card to pan/zoom to marker and open popup
        card.addEventListener('click', () => {
            AppState.map.setView([destination.coordinates.lat, destination.coordinates.lon], 10, { 
                animate: true,
                duration: CONFIG.UI.ANIMATION_DURATION
            });
            
            // Update distance control position after map animation completes
            setTimeout(() => {
                updateDistanceControl();
            }, CONFIG.UI.ANIMATION_DURATION + 100);
            
            marker.openPopup();
        });
    });
    
    // Add scroll to top button if there are many results
    if (destinations.length > 15) {
        const scrollToTopBtn = document.createElement('button');
        scrollToTopBtn.className = 'fixed bottom-4 right-4 bg-blue-500 text-white p-3 rounded-full shadow-lg hover:bg-blue-600 transition-colors z-50';
        scrollToTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
        scrollToTopBtn.title = 'Scroll to top';
        scrollToTopBtn.onclick = () => {
            const formContainer = document.querySelector('.form-container');
            if (formContainer) {
                formContainer.scrollTo({ top: 0, behavior: 'smooth' });
            }
        };
        document.body.appendChild(scrollToTopBtn);
        
        // Store reference for cleanup
        AppState.scrollToTopBtn = scrollToTopBtn;
    }
}

// Ensure form container stays within viewport
function ensureFormContainerInViewport() {
    const formContainer = document.querySelector('.form-container');
    if (!formContainer) return;
    
    const rect = formContainer.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Check if container goes outside viewport
    if (rect.right > viewportWidth) {
        const overflow = rect.right - viewportWidth;
        formContainer.style.left = Math.max(20, 65 - overflow) + 'px';
    }
    
    if (rect.bottom > viewportHeight) {
        const overflow = rect.bottom - viewportHeight;
        formContainer.style.top = Math.max(20, 50 - (overflow / viewportHeight * 100)) + '%';
    }
}

// Initialize application
function init() {
    initializeMap();
    setupDateSelector();
    setupLocationAutocomplete();
    setupFormSubmission();
    
    // Ensure form container is properly positioned
    setTimeout(ensureFormContainerInViewport, 100);
    
    // Recheck on window resize
    window.addEventListener('resize', ensureFormContainerInViewport);
}

// Cleanup function
function cleanup() {
    // Clean up distance circle manager
    if (AppState.distanceCircleManager) {
        AppState.distanceCircleManager.destroy();
        AppState.distanceCircleManager = null;
    }
    
    // Clean up map markers
    if (AppState.map) {
        AppState.markers.forEach(marker => {
            if (AppState.map.hasLayer(marker)) {
                AppState.map.removeLayer(marker);
            }
        });
        AppState.markers = [];
    }
    
    // Clean up scroll to top button
    if (AppState.scrollToTopBtn) {
        AppState.scrollToTopBtn.remove();
        AppState.scrollToTopBtn = null;
    }
    
    // Clean up event listeners
    const fromInput = document.getElementById('from');
    if (fromInput) {
        fromInput.removeEventListener('input', fromInput._debouncedSearch);
    }
    
    // Clean up map
    if (AppState.map) {
        AppState.map.remove();
        AppState.map = null;
    }
    
    // Clean up window event listeners
    window.removeEventListener('resize', ensureFormContainerInViewport);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// Cleanup on page unload
window.addEventListener('beforeunload', cleanup);