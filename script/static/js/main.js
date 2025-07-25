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
    debouncedFunctions: new Set(), // Track debounced functions for cleanup
    gridCellManager: null,
    currentMode: 'guided', // 'guided' or 'browse'
    currentData: null,
    currentDestinations: null,
    currentType: null,
    currentSort: null
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

    showError(message, containerId = 'initialResults') {
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
        // Clear both results containers
        const resultsDiv = document.getElementById('results');
        const initialResultsDiv = document.getElementById('initialResults');
        const browseResultsDiv = document.getElementById('browseResults');
        const modeTabsContainer = document.getElementById('modeTabsContainer');
        
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
        
        if (initialResultsDiv) {
            initialResultsDiv.innerHTML = '';
            initialResultsDiv.style.display = 'block'; // Show initialResults for new searches
        }
        
        if (browseResultsDiv) {
            browseResultsDiv.innerHTML = '';
        }
        
        // Hide mode tabs container when clearing results
        if (modeTabsContainer) {
            modeTabsContainer.style.display = 'none';
        }
        
        // Clear any active projections in browse mode
        if (AppState.gridCellManager) {
            AppState.gridCellManager.clearProjection();
        }
        
        // Remove existing markers from map
        AppState.markers.forEach(marker => {
            if (AppState.map && AppState.map.hasLayer(marker)) {
                AppState.map.removeLayer(marker);
            }
        });
        AppState.markers = [];
        
        // Clean up scroll to top button if it exists
        if (AppState.scrollToTopBtn) {
            AppState.scrollToTopBtn.remove();
            AppState.scrollToTopBtn = null;
        }
        
        // Reset state
        AppState.currentTab = null;
        AppState.tabButtons = null;
        AppState.currentData = null;
        AppState.currentDestinations = null;
        AppState.currentType = null;
        AppState.currentSort = null;
        AppState.currentMode = 'guided'; // Reset to guided mode
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
        this.radius = 50; // miles
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
                const initialResultsDiv = document.getElementById('initialResults');
                if (initialResultsDiv) {
                    initialResultsDiv.innerHTML = '<p class="text-center text-gray-500">No destinations found within your criteria.</p>';
                }
                return;
            }

            // Show mode tabs and display results in guided mode
            showModeTabsWithResults(data);
        } catch (error) {
            console.error('Error:', error);
            
            // Determine the correct error container based on current state
            let errorContainer = 'initialResults';
            const modeTabsContainer = document.getElementById('modeTabsContainer');
            
            if (modeTabsContainer && modeTabsContainer.style.display !== 'none') {
                // Mode tabs are visible, show error in results
                errorContainer = 'results';
            }
            
            console.log('Showing error in container:', errorContainer);
            
            if (error.name === 'AbortError') {
                Utils.showError('Request timed out. Please try again.', errorContainer);
            } else {
                Utils.showError('An error occurred while searching for destinations. Please try again.', errorContainer);
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
    
    // Create tabs container
    const tabsContainer = document.createElement('div');
    tabsContainer.className = 'mb-6';
    
    // Create tab buttons
    const tabButtons = document.createElement('div');
    tabButtons.className = 'flex border-b border-gray-200 mb-4';
    
    const sunnyTab = document.createElement('button');
    sunnyTab.className = 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600 bg-white';
    sunnyTab.textContent = `Sunny Destinations (${data.sunny_destinations ? data.sunny_destinations.length : 0})`;
    sunnyTab.onclick = () => switchTab('sunny', AppState.currentData);
    
    const comfortTab = document.createElement('button');
    comfortTab.className = 'px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 hover:border-gray-300';
    comfortTab.textContent = `Comfortable Destinations (${data.comfortable_destinations ? data.comfortable_destinations.length : 0})`;
    comfortTab.onclick = () => switchTab('comfort', AppState.currentData);
    
    tabButtons.appendChild(sunnyTab);
    tabButtons.appendChild(comfortTab);
    tabsContainer.appendChild(tabButtons);
    
    // Create content container
    const contentContainer = document.createElement('div');
    contentContainer.id = 'tab-content';
    tabsContainer.appendChild(contentContainer);
    
    resultsDiv.appendChild(tabsContainer);
    
    // Store tab state and data
    AppState.currentTab = 'sunny';
    AppState.tabButtons = { sunny: sunnyTab, comfort: comfortTab };
    AppState.currentData = data;
    
    // Show sunny destinations by default
    if (data.sunny_destinations && data.sunny_destinations.length > 0) {
        displaySunnyDestinations(data.sunny_destinations);
    }

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
    
    // Update stored data
    AppState.currentData = data;
    
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
    
    // --- Sort Dropdown UI ---
    const sortContainer = document.createElement('div');
    sortContainer.className = 'mb-4 flex items-center justify-end relative w-full';
    
    // Sort icon button
    const sortBtn = document.createElement('button');
    sortBtn.className = 'w-full flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm';
    sortBtn.innerHTML = `<i class="fas fa-sort mr-2 text-gray-600"></i><span id="current-sort-label" class="text-gray-700 font-medium">Sort by: Score</span><i class="fas fa-chevron-down ml-2 text-gray-500 text-xs"></i>`;
    sortContainer.appendChild(sortBtn);
    
    // Dropdown menu
    const dropdown = document.createElement('div');
    dropdown.className = 'hidden sort-dropdown';
    dropdown.innerHTML = `
        <button data-sort="score">Score</button>
        <button data-sort="distance">Distance</button>
        <button data-sort="temperature">Temperature</button>
    `;
    sortContainer.appendChild(dropdown);
    contentContainer.appendChild(sortContainer);
    
    // Dropdown logic
    let currentSort = 'score';
    const sortLabel = sortBtn.querySelector('#current-sort-label');
    const chevronIcon = sortBtn.querySelector('.fa-chevron-down');
    
    sortBtn.onclick = (e) => {
        e.stopPropagation();
        const isHidden = dropdown.classList.contains('hidden');
        dropdown.classList.toggle('hidden');
        
        // Update button appearance
        if (isHidden) {
            sortBtn.classList.add('ring-2', 'ring-blue-500', 'border-blue-500');
            chevronIcon.classList.remove('fa-chevron-down');
            chevronIcon.classList.add('fa-chevron-up');
        } else {
            sortBtn.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
            chevronIcon.classList.remove('fa-chevron-up');
            chevronIcon.classList.add('fa-chevron-down');
        }
    };
    // Dropdown option click
    dropdown.querySelectorAll('button[data-sort]').forEach(btn => {
        btn.onclick = (e) => {
            const sortType = btn.getAttribute('data-sort');
            currentSort = sortType;
            sortLabel.textContent = 'Sort by: ' + (sortType === 'score' ? 'Score' : sortType.charAt(0).toUpperCase() + sortType.slice(1));
            dropdown.classList.add('hidden');
            
            // Reset button appearance
            sortBtn.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
            chevronIcon.classList.remove('fa-chevron-up');
            chevronIcon.classList.add('fa-chevron-down');
            
            sortDestinations(sortType);
        };
    });
    // Close dropdown on outside click
    document.addEventListener('click', function closeDropdown(e) {
        if (!sortContainer.contains(e.target)) {
            dropdown.classList.add('hidden');
            // Reset button appearance
            sortBtn.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
            chevronIcon.classList.remove('fa-chevron-up');
            chevronIcon.classList.add('fa-chevron-down');
        }
    });
    
    // Store current destinations for sorting
    AppState.currentDestinations = [...destinations];
    AppState.currentType = type;
    AppState.currentSort = currentSort;
    
    // Initial sort
    sortDestinations(currentSort);
}

// Sort destinations based on criteria (descending only)
function sortDestinations(criteria) {
    if (!AppState.currentDestinations || !AppState.currentType) return;
    let sortedDestinations = [...AppState.currentDestinations];
    switch (criteria) {
        case 'score': {
            const scoreKey = AppState.currentType === 'sunny' ? 'sunny_score' : 'comfort_score';
            sortedDestinations.sort((a, b) => b[scoreKey] - a[scoreKey]);
            break;
        }
        case 'distance':
            sortedDestinations.sort((a, b) => a.distance - b.distance);
            break;
        case 'temperature':
            sortedDestinations.sort((a, b) => b.max_temp - a.max_temp);
            break;
    }
    renderDestinations(sortedDestinations, AppState.currentType);
}

// Render destinations without recreating sort controls
function renderDestinations(destinations, type) {
    const contentContainer = document.getElementById('tab-content');
    if (!contentContainer) return;
    
    // Remove existing result cards and counter, keep sort controls
    const sortContainer = contentContainer.querySelector('.mb-4.flex.items-center.justify-end.relative');
    
    // Clear everything except sort controls
    contentContainer.innerHTML = '';
    if (sortContainer) contentContainer.appendChild(sortContainer);
    
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
    
    // Clear existing markers
    AppState.markers.forEach(marker => {
        if (AppState.map.hasLayer(marker)) {
            AppState.map.removeLayer(marker);
        }
    });
    AppState.markers = [];
    
    destinations.forEach((destination, idx) => {
        // Create result card
        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg shadow-md p-3 hover:shadow-lg transition-shadow mb-2 cursor-pointer';
        
        // Format temperature display
        let tempDisplay = '';
        if (destination.min_temp !== undefined && destination.max_temp !== undefined) {
            if (destination.min_temp === destination.max_temp) {
                tempDisplay = `${destination.min_temp}°C`;
            } else {
                tempDisplay = `${destination.min_temp}°C - ${destination.max_temp}°C`;
            }
        }
        
        card.innerHTML = `
            <div class="result-card-content">
                <div class="result-card-info">
                    <h3 class="font-bold text-lg">${destination.city}</h3>
                    <p class="text-gray-600">${destination.region}, ${destination.country}</p>
                    <p class="text-gray-500">${Math.round(destination.distance)} miles away</p>
                    ${tempDisplay ? `<p class="text-gray-500 text-sm">🌡️ ${tempDisplay}</p>` : ''}
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
                ${tempDisplay ? `🌡️ ${tempDisplay}<br>` : ''}
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
    // if (destinations.length > 15) {
    //     const scrollToTopBtn = document.createElement('button');
    //     scrollToTopBtn.className = 'fixed bottom-4 right-4 bg-blue-500 text-white p-3 rounded-full shadow-lg hover:bg-blue-600 transition-colors z-50';
    //     scrollToTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    //     scrollToTopBtn.title = 'Scroll to top';
    //     scrollToTopBtn.onclick = () => {
    //         const formContainer = document.querySelector('.form-container');
    //         if (formContainer) {
    //             formContainer.scrollTo({ top: 0, behavior: 'smooth' });
    //         }
    //     };
    //     document.body.appendChild(scrollToTopBtn);
        
    //     // Store reference for cleanup
    //     AppState.scrollToTopBtn = scrollToTopBtn;
    // }
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

// Mode management functions
function showModeTabsWithResults(data) {
    const modeTabsContainer = document.getElementById('modeTabsContainer');
    const initialResults = document.getElementById('initialResults');
    
    if (!modeTabsContainer) return;
    
    // Hide initial results and show mode tabs container
    if (initialResults) initialResults.style.display = 'none';
    modeTabsContainer.style.display = 'block';
    
    // Store the data
    AppState.currentData = data;
    
    // Set initial mode to guided
    AppState.currentMode = 'guided';
    
    // Ensure proper content visibility for guided mode
    const guidedContent = document.getElementById('guidedModeContent');
    const browseContent = document.getElementById('browseModeContent');
    
    if (guidedContent) guidedContent.style.display = 'block';
    if (browseContent) browseContent.style.display = 'none';
    
    // Update tab styles and display results
    updateModeTabStyles();
    displayResults(data);
}

function setupModeTabsNavigation() {
    const guidedModeTab = document.getElementById('guidedModeTab');
    const browseModeTab = document.getElementById('browseModeTab');
    
    if (!guidedModeTab || !browseModeTab) return;
    
    guidedModeTab.addEventListener('click', () => {
        switchToMode('guided');
    });
    
    browseModeTab.addEventListener('click', () => {
        switchToMode('browse');
    });
}

function switchToMode(mode) {
    if (AppState.currentMode === mode) return;
    
    AppState.currentMode = mode;
    updateModeTabStyles();
    
    const guidedContent = document.getElementById('guidedModeContent');
    const browseContent = document.getElementById('browseModeContent');
    
    if (mode === 'guided') {
        if (guidedContent) guidedContent.style.display = 'block';
        if (browseContent) browseContent.style.display = 'none';
        
        // Clear any projections when switching to guided mode
        if (AppState.gridCellManager) {
            AppState.gridCellManager.clearProjection();
        }
        
        // Restore guided mode markers to the map
        restoreGuidedModeMarkers();
        
        // Display guided mode results if available
        if (AppState.currentData) {
            displayResults(AppState.currentData);
        }
    } else {
        if (guidedContent) guidedContent.style.display = 'none';
        if (browseContent) browseContent.style.display = 'block';
        
        // Clear guided mode markers from the map when switching to browse mode
        clearGuidedModeMarkers();
        
        // Clear browse results and initialize browse mode
        const browseResults = document.getElementById('browseResults');
        if (browseResults) {
            browseResults.innerHTML = '';
        }
        
        // Initialize browse mode with appropriate messaging
        initializeBrowseMode();
    }
}

function updateModeTabStyles() {
    const guidedModeTab = document.getElementById('guidedModeTab');
    const browseModeTab = document.getElementById('browseModeTab');
    
    if (!guidedModeTab || !browseModeTab) return;
    
    // Reset all tab styles
    guidedModeTab.className = 'mode-tab px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 hover:border-gray-300';
    browseModeTab.className = 'mode-tab px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 hover:border-gray-300';
    
    // Set active tab style
    if (AppState.currentMode === 'guided') {
        guidedModeTab.className = 'mode-tab px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600 bg-white';
    } else {
        browseModeTab.className = 'mode-tab px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600 bg-white';
    }
}

// Helper functions for managing guided mode markers
function clearGuidedModeMarkers() {
    // Hide all destination markers
    AppState.markers.forEach(marker => {
        if (AppState.map.hasLayer(marker)) {
            AppState.map.removeLayer(marker);
        }
    });
    
    // Keep the starting point marker and distance circle visible for Browse Mode
    // as they're needed for the projection functionality
}

function restoreGuidedModeMarkers() {
    // Restore all destination markers
    AppState.markers.forEach(marker => {
        if (!AppState.map.hasLayer(marker)) {
            marker.addTo(AppState.map);
        }
    });
}

function initializeBrowseMode() {
    const browseResults = document.getElementById('browseResults');
    if (!browseResults) return;
    
    // Clear any existing content
    browseResults.innerHTML = '';
    
    // Check if we have a starting location
    if (!AppState.distanceCircleManager || !AppState.distanceCircleManager.center) {
        browseResults.innerHTML = `
            <div class="text-center p-6 bg-blue-50 rounded-lg border border-blue-200">
                <i class="fas fa-info-circle text-blue-500 text-2xl mb-3"></i>
                <h3 class="font-semibold text-blue-800 mb-2">Getting Started with Browse Mode</h3>
                <p class="text-blue-700 text-sm mb-4">
                    To use weather projections, please first set a starting location by performing a search in Guided Mode.
                </p>
                <p class="text-blue-600 text-xs">
                    Once you have a starting location, you can project weather indices across the grid system.
                </p>
            </div>
        `;
    } else {
        const center = AppState.distanceCircleManager.center;
        const radius = AppState.distanceCircleManager.radius;
        
        browseResults.innerHTML = `
            <div class="text-center p-4 bg-green-50 rounded-lg border border-green-200">
                <i class="fas fa-check-circle text-green-500 text-xl mb-2"></i>
                <h3 class="font-semibold text-green-800 mb-2">Ready for Weather Projections</h3>
                <p class="text-green-700 text-sm mb-2">
                    Starting location: ${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}
                </p>
                <p class="text-green-600 text-xs">
                    Search radius: ${radius} miles • Click a projection button above to begin
                </p>
            </div>
        `;
    }
}

// Weather projection management
class WeatherProjectionManager {
    constructor(map) {
        this.map = map;
        this.gridCells = [];
        this.currentProjection = null; // 'sunny', 'comfort', or null
        this.isLoading = false;
    }

    async projectIndex(indexType, centerLat, centerLon, radiusMiles) {
        if (this.isLoading) return;
        
        try {
            this.isLoading = true;
            this.showProjectionLoading(indexType, true);
            
            // Clear existing projection
            this.clearProjection();
            
            // Get current search parameters from the form or use defaults
            const dateInput = document.getElementById('date');
            const startHourInput = document.getElementById('start_hour');
            const endHourInput = document.getElementById('end_hour');
            
            const targetDate = dateInput ? dateInput.value : new Date().toISOString().split('T')[0];
            const startHour = startHourInput ? parseInt(startHourInput.value) : 9;
            const endHour = endHourInput ? parseInt(endHourInput.value) : 17;
            
            // Fetch real weather data for cells within radius
            const params = new URLSearchParams({
                lat: centerLat,
                lon: centerLon,
                radius: radiusMiles,
                index_type: indexType,
                date: targetDate,
                start_hour: startHour,
                end_hour: endHour
            });
            
            const response = await fetch(`/project-weather-index?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Create colored cells using real weather scores
            let successfulCells = 0;
            data.cells.forEach(cell => {
                if (cell.weather_score && cell.weather_score.score > 0) {
                    this.createProjectedCell(cell, indexType, cell.weather_score.score, cell.weather_score);
                    successfulCells++;
                }
            });
            
            if (successfulCells === 0) {
                throw new Error('No weather data available for any grid cells in the selected area');
            }
            
            this.currentProjection = indexType;
            this.showLegend(indexType);
            this.showClearButton();
            this.setActiveButton(indexType);
            
            console.log(`Projected ${indexType} index for ${data.cells.length} grid cells using real weather data`);
            console.log(`Date: ${data.target_date}, Time: ${data.time_range}`);
            
            // Update browse results with projection info
            this.updateBrowseResults(data);
            
        } catch (error) {
            console.error('Error projecting index:', error);
            Utils.showError('Error loading projection: ' + error.message, 'browseResults');
        } finally {
            this.isLoading = false;
            this.showProjectionLoading(indexType, false);
        }
    }

    createProjectedCell(cell, indexType, value, weatherScore = null) {
        const boundaries = cell.boundaries;
        if (!boundaries || boundaries.length < 4) return;
        
        // Convert boundaries to Leaflet LatLng format
        const polygonPoints = boundaries.map(point => [point.latitude, point.longitude]);
        
        // Get color based on index type and value
        const { color, fillColor, className } = this.getProjectionColors(indexType, value);
        
        // Create polygon with projection colors
        const polygon = L.polygon(polygonPoints, {
            color: color,
            fillColor: fillColor,
            fillOpacity: 0.6,
            weight: 1.5,
            opacity: 0.8,
            className: className
        });
        
        // Add popup with projection info
        const indexName = indexType === 'sunny' ? 'Sunny' : 'Comfort';
        const level = weatherScore ? weatherScore.level : this.getIndexLevel(value);
        const closestLocation = weatherScore ? weatherScore.closest_location : 'Unknown';
        
        // Use actual location name from weather data instead of Grid Cell #
        const locationName = weatherScore && weatherScore.closest_location && weatherScore.closest_location !== 'Unknown'
            ? weatherScore.closest_location 
            : `Grid Cell #${cell.id}`;
        
        let popupContent = `
            <div class="text-center">
                <strong>${locationName}</strong><br>
                <div class="mt-2 p-2 rounded" style="background: ${fillColor}; color: white; font-weight: bold;">
                    ${indexName} Index: ${value}/10
                </div>
                <small class="text-gray-600 mt-1 block">Level: ${level}</small><br>
                <small>Center: ${cell.center.latitude.toFixed(4)}, ${cell.center.longitude.toFixed(4)}</small>`;
        
        if (weatherScore && weatherScore.closest_location !== 'Unknown') {
            const distance = weatherScore.distance_to_station;
            const distanceText = distance ? ` (${distance} miles away)` : '';
            popupContent += `<br><small class="text-blue-600">Data from: ${closestLocation}${distanceText}</small>`;
        }
        
        popupContent += `</div>`;
        
        polygon.bindPopup(popupContent);
        
        // Add to map and store reference
        polygon.addTo(this.map);
        this.gridCells.push({ polygon, value, type: indexType, weatherScore });
    }

    getProjectionColors(indexType, value) {
        if (indexType === 'sunny') {
            // Sunny index colors: More distinct color progression ending in light brown orange
            if (value <= 3) {
                return {
                    color: '#991b1b',      // Very dark red border
                    fillColor: '#dc2626',  // Dark red fill
                    className: 'grid-cell-low'
                };
            } else if (value <= 5) {
                return {
                    color: '#c2410c',      // Dark orange border
                    fillColor: '#ea580c',  // Orange fill
                    className: 'grid-cell-medium'
                };
            } else if (value <= 7) {
                return {
                    color: '#a16207',      // Dark amber border
                    fillColor: '#d97706',  // Amber fill
                    className: 'grid-cell-medium'
                };
            } else {
                return {
                    color: '#92400e',      // Light brown border
                    fillColor: '#d97706',  // Light brown orange fill
                    className: 'grid-cell-high'
                };
            }
        } else {
            // Comfort index colors: blue (low) to green (high)
            if (value <= 3) {
                return {
                    color: '#dc2626',      // Red border for very uncomfortable
                    fillColor: '#ef4444',  // Red fill
                    className: 'grid-cell-low'
                };
            } else if (value <= 5) {
                return {
                    color: '#2563eb',      // Blue border for uncomfortable
                    fillColor: '#3b82f6',  // Blue fill
                    className: 'grid-cell-medium'
                };
            } else if (value <= 7) {
                return {
                    color: '#0891b2',      // Cyan border for moderate
                    fillColor: '#06b6d4',  // Cyan fill
                    className: 'grid-cell-medium'
                };
            } else {
                return {
                    color: '#059669',      // Green border for comfortable
                    fillColor: '#10b981',  // Green fill
                    className: 'grid-cell-high'
                };
            }
        }
    }

    getIndexLevel(value) {
        if (value <= 3) return 'Poor';
        if (value <= 5) return 'Fair'; 
        if (value <= 7) return 'Good';
        return 'Excellent';
    }

    showLegend(indexType) {
        const legend = document.getElementById('indexLegend');
        const legendContent = document.getElementById('legendContent');
        
        if (!legend || !legendContent) return;
        
        legendContent.innerHTML = '';
        
        let levels;
        if (indexType === 'sunny') {
            levels = [
                { range: '1-3', level: 'Poor', value: 2 },
                { range: '4-5', level: 'Fair', value: 4.5 },
                { range: '6-7', level: 'Good', value: 6.5 },
                { range: '8-10', level: 'Excellent', value: 9 }
            ];
        } else {
            levels = [
                { range: '1-3', level: 'Very Uncomfortable', value: 2 },
                { range: '4-5', level: 'Uncomfortable', value: 4.5 },
                { range: '6-7', level: 'Moderate', value: 6.5 },
                { range: '8-10', level: 'Comfortable', value: 9 }
            ];
        }
        
        levels.forEach(item => {
            const { fillColor } = this.getProjectionColors(indexType, item.value);
            
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';
            legendItem.innerHTML = `
                <div class="legend-color" style="background-color: ${fillColor};"></div>
                <span>${item.level} (${item.range})</span>
            `;
            legendContent.appendChild(legendItem);
        });
        
        legend.style.display = 'block';
    }

    hideLegend() {
        const legend = document.getElementById('indexLegend');
        if (legend) {
            legend.style.display = 'none';
        }
    }

    showClearButton() {
        const clearButton = document.getElementById('clearProjectionButton');
        if (clearButton) {
            clearButton.style.display = 'block';
        }
    }

    hideClearButton() {
        const clearButton = document.getElementById('clearProjectionButton');
        if (clearButton) {
            clearButton.style.display = 'none';
        }
    }

    setActiveButton(indexType) {
        const sunnyButton = document.getElementById('projectSunnyButton');
        const comfortButton = document.getElementById('projectComfortButton');
        
        // Remove active class from both buttons
        if (sunnyButton) sunnyButton.classList.remove('active');
        if (comfortButton) comfortButton.classList.remove('active');
        
        // Add active class to current button
        if (indexType === 'sunny' && sunnyButton) {
            sunnyButton.classList.add('active');
        } else if (indexType === 'comfort' && comfortButton) {
            comfortButton.classList.add('active');
        }
    }

    clearActiveButtons() {
        const sunnyButton = document.getElementById('projectSunnyButton');
        const comfortButton = document.getElementById('projectComfortButton');
        
        if (sunnyButton) sunnyButton.classList.remove('active');
        if (comfortButton) comfortButton.classList.remove('active');
    }

    clearProjection() {
        this.gridCells.forEach(item => {
            if (this.map.hasLayer(item.polygon)) {
                this.map.removeLayer(item.polygon);
            }
        });
        this.gridCells = [];
        this.currentProjection = null;
        this.hideLegend();
        this.hideClearButton();
        this.clearActiveButtons();
    }

    showProjectionLoading(indexType, show = true) {
        const buttonId = indexType === 'sunny' ? 'projectSunnyButton' : 'projectComfortButton';
        const textId = indexType === 'sunny' ? 'projectSunnyButtonText' : 'projectComfortButtonText';
        const spinnerId = indexType === 'sunny' ? 'projectSunnyButtonSpinner' : 'projectComfortButtonSpinner';
        
        const button = document.getElementById(buttonId);
        const buttonText = document.getElementById(textId);
        const buttonSpinner = document.getElementById(spinnerId);
        
        if (show) {
            if (button) button.classList.add('loading');
            if (buttonText) buttonText.style.opacity = '0.7';
            if (buttonSpinner) buttonSpinner.style.display = 'inline-block';
        } else {
            if (button) button.classList.remove('loading');
            if (buttonText) buttonText.style.opacity = '1';
            if (buttonSpinner) buttonSpinner.style.display = 'none';
        }
    }

    updateBrowseResults(projectionData) {
        const browseResults = document.getElementById('browseResults');
        if (!browseResults) return;
        
        // Create summary information about the projection
        const totalCells = projectionData.total_cells;
        const indexType = projectionData.index_type;
        const targetDate = projectionData.target_date;
        const timeRange = projectionData.time_range;
        
        // Calculate statistics
        const scores = projectionData.cells
            .filter(cell => cell.weather_score && cell.weather_score.score > 0)
            .map(cell => cell.weather_score.score);
        
        if (scores.length === 0) {
            browseResults.innerHTML = `
                <div class="text-center p-4 bg-red-50 rounded-lg border border-red-200">
                    <i class="fas fa-exclamation-triangle text-red-500 text-xl mb-2"></i>
                    <h3 class="font-semibold text-red-800 mb-2">No Weather Data Available</h3>
                    <p class="text-red-700 text-sm">
                        No weather data found for the projected area on ${targetDate}.
                    </p>
                </div>
            `;
            return;
        }
        
        const avgScore = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
        const maxScore = Math.max(...scores).toFixed(1);
        const minScore = Math.min(...scores).toFixed(1);
        
        const indexName = indexType === 'sunny' ? 'Sunny' : 'Comfort';
        const iconClass = indexType === 'sunny' ? 'fas fa-sun text-yellow-500' : 'fas fa-thermometer-half text-green-500';
        
        browseResults.innerHTML = `
            <div class="bg-blue-50 rounded-lg border border-blue-200 p-4">
                <div class="flex items-center mb-3">
                    <i class="${iconClass} text-xl mr-2"></i>
                    <h3 class="font-semibold text-blue-800">${indexName} Index Projection Results</h3>
                </div>
                
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div class="text-blue-600 font-medium">Date & Time</div>
                        <div class="text-blue-800">${targetDate}</div>
                        <div class="text-blue-700">${timeRange}</div>
                    </div>
                    <div>
                        <div class="text-blue-600 font-medium">Coverage</div>
                        <div class="text-blue-800">${totalCells} grid cells</div>
                        <div class="text-blue-700">${scores.length} with data</div>
                    </div>
                    <div>
                        <div class="text-blue-600 font-medium">Score Range</div>
                        <div class="text-blue-800">${minScore} - ${maxScore}</div>
                        <div class="text-blue-700">Average: ${avgScore}</div>
                    </div>
                    <div>
                        <div class="text-blue-600 font-medium">Best Areas</div>
                        <div class="text-blue-800">${scores.filter(s => s >= 7).length} high scoring</div>
                        <div class="text-blue-700">${scores.filter(s => s >= 5).length} moderate+</div>
                    </div>
                </div>
                
                <div class="mt-3 text-xs text-blue-600">
                    💡 Click on any colored cell on the map for detailed weather information
                </div>
            </div>
        `;
    }

    destroy() {
        this.clearProjection();
    }
}

// Set up projection buttons functionality
function setupProjectionButtons() {
    const projectSunnyButton = document.getElementById('projectSunnyButton');
    const projectComfortButton = document.getElementById('projectComfortButton');
    const clearProjectionButton = document.getElementById('clearProjectionButton');
    
    if (!projectSunnyButton || !projectComfortButton || !clearProjectionButton) {
        console.warn('Projection buttons not found');
        return;
    }
    
    // Initialize weather projection manager
    AppState.gridCellManager = new WeatherProjectionManager(AppState.map);
    
    // Project Sunny Index button
    projectSunnyButton.addEventListener('click', async function() {
        // Check if we have a starting location
        if (!AppState.distanceCircleManager || !AppState.distanceCircleManager.center) {
            Utils.showError('Please select a starting location first.', 'browseResults');
            return;
        }
        
        const center = AppState.distanceCircleManager.center;
        const radius = AppState.distanceCircleManager.radius;
        
        AppState.gridCellManager.projectIndex('sunny', center.lat, center.lng, radius);
    });
    
    // Project Comfort Index button
    projectComfortButton.addEventListener('click', async function() {
        // Check if we have a starting location
        if (!AppState.distanceCircleManager || !AppState.distanceCircleManager.center) {
            Utils.showError('Please select a starting location first.', 'browseResults');
            return;
        }
        
        const center = AppState.distanceCircleManager.center;
        const radius = AppState.distanceCircleManager.radius;
        
        AppState.gridCellManager.projectIndex('comfort', center.lat, center.lng, radius);
    });
    
    // Clear projection button
    clearProjectionButton.addEventListener('click', function() {
        AppState.gridCellManager.clearProjection();
    });
}

// Initialize application
function init() {
    initializeMap();
    setupDateSelector();
    setupLocationAutocomplete();
    setupFormSubmission();
    setupProjectionButtons();
    setupModeTabsNavigation();
    
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
    
    // Clean up grid cell manager
    if (AppState.gridCellManager) {
        AppState.gridCellManager.destroy();
        AppState.gridCellManager = null;
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