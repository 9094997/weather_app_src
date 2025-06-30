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
    radiusCircle: null,
    startPointMarker: null,
    distanceControl: null,
    distanceLabel: null,
    isLoading: false,
    currentSearch: null
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
            buttonText.textContent = 'Find Sunny Destinations';
            buttonSpinner.style.display = 'none';
        }
    },

    showError(message, containerId = 'results') {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                ${message}
            </div>
        `;
    },

    clearResults() {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '';
        
        // Remove old markers
        AppState.markers.forEach(marker => {
            if (AppState.map.hasLayer(marker)) {
                AppState.map.removeLayer(marker);
            }
        });
        AppState.markers = [];
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

    // Update control position when map moves
    AppState.map.on('move', updateDistanceControl);
    AppState.map.on('zoom', updateDistanceControl);
    AppState.map.on('moveend', updateDistanceControl);
    AppState.map.on('zoomend', updateDistanceControl);
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

// Update distance value display and map radius
function updateDistance(value) {
    const distanceValue = document.getElementById('distanceValue');
    distanceValue.textContent = Math.round(value);
    
    if (AppState.radiusCircle) {
        AppState.radiusCircle.setRadius(value * 1609.34);
        updateDistanceControl();
    }
}

// Interactive distance ring functionality
function createDistanceControl() {
    // Clean up existing controls if they exist
    if (AppState.distanceControl) {
        document.body.removeChild(AppState.distanceControl);
    }
    if (AppState.distanceLabel) {
        document.body.removeChild(AppState.distanceLabel);
    }
    
    // Create distance control element
    AppState.distanceControl = document.createElement('div');
    AppState.distanceControl.className = 'distance-control';
    AppState.distanceControl.innerHTML = `
        <div class="distance-control-handle"></div>
    `;
    AppState.distanceControl.style.display = 'none'; // Initially hidden
    document.body.appendChild(AppState.distanceControl);

    // Create distance label
    AppState.distanceLabel = document.createElement('div');
    AppState.distanceLabel.className = 'distance-label';
    AppState.distanceLabel.innerHTML = `
        <div class="distance-label-content">
            <span class="distance-value">200</span>
            <span class="distance-unit">miles</span>
        </div>
    `;
    AppState.distanceLabel.style.display = 'none'; // Initially hidden
    document.body.appendChild(AppState.distanceLabel);

    let isDragging = false;
    let startY = 0;
    let startDistance = 0;

    const handleMouseDown = (e) => {
        e.preventDefault();
        e.stopPropagation();
        isDragging = true;
        startY = e.clientY;
        startDistance = parseInt(document.getElementById('distance').value);
        document.body.style.userSelect = 'none';
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    };

    const handleMouseMove = (e) => {
        if (!isDragging) return;
        
        const deltaY = startY - e.clientY;
        const distanceChange = Math.round(deltaY / 2);
        const newDistance = Math.max(1, Math.min(200, startDistance + distanceChange));
        
        document.getElementById('distance').value = newDistance;
        updateDistance(newDistance);
    };

    const handleMouseUp = () => {
        isDragging = false;
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
    };

    AppState.distanceControl.addEventListener('mousedown', handleMouseDown);
    AppState.cleanupDistanceControl = () => {
        AppState.distanceControl.removeEventListener('mousedown', handleMouseDown);
    };
}

function updateDistanceControl() {
    if (!AppState.distanceControl || !AppState.radiusCircle) return;
    
    const mapContainer = AppState.map.getContainer();
    const mapRect = mapContainer.getBoundingClientRect();
    const center = AppState.map.latLngToContainerPoint(AppState.radiusCircle.getLatLng());
    
    // Check if the center point is within the visible map area
    if (center.x < 0 || center.x > mapRect.width || center.y < 0 || center.y > mapRect.height) {
        // Hide controls if center is not visible
        AppState.distanceControl.style.display = 'none';
        AppState.distanceLabel.style.display = 'none';
        return;
    }
    
    // Show controls if they were hidden
    AppState.distanceControl.style.display = 'flex';
    AppState.distanceLabel.style.display = 'block';
    
    // Position the distance control at the edge of the circle
    const radius = AppState.radiusCircle.getRadius() / AppState.map.getMetersPerPixel();
    const angle = Math.PI / 4; // 45 degrees
    const x = center.x + radius * Math.cos(angle);
    const y = center.y - radius * Math.sin(angle);
    
    // Ensure the control stays within the map bounds
    const controlX = Math.max(10, Math.min(mapRect.width - 10, mapRect.left + x - 10));
    const controlY = Math.max(10, Math.min(mapRect.height - 10, mapRect.top + y - 10));
    
    AppState.distanceControl.style.left = `${controlX}px`;
    AppState.distanceControl.style.top = `${controlY}px`;
    
    // Position the distance label
    const labelX = Math.max(10, Math.min(mapRect.width - 60, mapRect.left + x + 20));
    const labelY = Math.max(10, Math.min(mapRect.height - 20, mapRect.top + y - 15));
    
    AppState.distanceLabel.style.left = `${labelX}px`;
    AppState.distanceLabel.style.top = `${labelY}px`;
    
    const distanceValue = document.getElementById('distance').value;
    AppState.distanceLabel.querySelector('.distance-value').textContent = distanceValue;
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
    // Remove existing radius circle and start point marker
    if (AppState.radiusCircle) {
        AppState.map.removeLayer(AppState.radiusCircle);
    }
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

    // Create radius circle
    AppState.radiusCircle = L.circle([coordinates.lat, coordinates.lon], {
        radius: document.getElementById('distance').value * 1609.34,
        color: '#3B82F6',
        fillColor: '#93C5FD',
        fillOpacity: 0.2,
        weight: 2
    }).addTo(AppState.map);

    AppState.map.setView([coordinates.lat, coordinates.lon], 8);
    
    // Update distance control position
    setTimeout(updateDistanceControl, 100);
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

            if (data.length === 0) {
                document.getElementById('results').innerHTML = 
                    '<p class="text-center text-gray-500">No sunny destinations found within your criteria.</p>';
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

// Display search results
function displayResults(data) {
    const resultsDiv = document.getElementById('results');

    data.forEach((destination, idx) => {
        // Create result card
        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow mb-2 cursor-pointer';
        card.innerHTML = `
            <div class="result-card-content">
                <div class="result-card-info">
                    <h3 class="font-bold text-lg">${destination.index}. ${destination.city}</h3>
                    <p class="text-gray-600">${destination.region}, ${destination.country}</p>
                    <p class="text-gray-500">${Math.round(destination.distance)} miles away</p>
                    <div class="sunny-score-info mt-2">
                        <div class="flex items-center">
                            <i class="fas fa-sun text-yellow-500 mr-2"></i>
                            <span class="font-semibold text-lg">${destination.sunny_score}/10</span>
                            <span class="ml-2 text-sm text-gray-600">(${destination.sunny_level})</span>
                        </div>
                    </div>
                </div>
                <div class="flex flex-col items-center justify-center">
                    <div class="sunny-score-circle mb-2">
                        <div class="w-16 h-16 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-white font-bold text-lg">
                            ${destination.sunny_score}
                        </div>
                    </div>
                    <p class="text-sm text-gray-600">Sunny Score</p>
                </div>
            </div>
        `;
        resultsDiv.appendChild(card);

        // Create custom icon for the marker with sunny score
        const sunnyIcon = L.divIcon({
            className: 'sunny-marker-icon',
            html: `
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-white font-bold text-xs border-2 border-white shadow-lg">
                    ${destination.sunny_score}
                </div>
            `,
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });

        // Create marker with custom icon
        const marker = L.marker([destination.coordinates.lat, destination.coordinates.lon], {
            icon: sunnyIcon
        })
        .addTo(AppState.map)
        .bindPopup(`
            <div class="text-center">
                <div class="sunny-score-circle inline-block mb-2">
                    <div class="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-white font-bold text-sm">
                        ${destination.sunny_score}
                    </div>
                </div>
                <strong>${destination.index}. ${destination.city}</strong><br>
                ${destination.region}, ${destination.country}<br>
                <span class="text-yellow-600 font-semibold">${destination.sunny_level}</span><br>
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
}

// Initialize application
function init() {
    initializeMap();
    setupDateSelector();
    createDistanceControl();
    setupLocationAutocomplete();
    setupFormSubmission();
}

// Cleanup function
function cleanup() {
    if (AppState.cleanupDistanceControl) {
        AppState.cleanupDistanceControl();
    }
    if (AppState.distanceControl) {
        document.body.removeChild(AppState.distanceControl);
    }
    if (AppState.distanceLabel) {
        document.body.removeChild(AppState.distanceLabel);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// Cleanup on page unload
window.addEventListener('beforeunload', cleanup);