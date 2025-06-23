// static/js/main.js

// Initialize the map with zoom control disabled
const map = L.map('map', {
    zoomControl: false  // Disable zoom control
}).setView([54.5, -2], 6); // Center on UK

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Store markers and circle
let markers = [];
let radiusCircle = null;
let startPointMarker = null;
let distanceControl = null;
let distanceLabel = null;

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

// Call setup function when page loads
setupDateSelector();

// Create custom icon class
const WeatherIcon = L.Icon.extend({
    options: {
        iconSize: [40, 40],
        iconAnchor: [20, 20],
        popupAnchor: [0, -20]
    }
});

// Weather icon selection
const weatherIcons = document.querySelectorAll('.weather-icon');
const weatherInput = document.getElementById('weather');

weatherIcons.forEach(icon => {
    icon.addEventListener('click', function() {
        weatherIcons.forEach(i => i.classList.remove('selected'));
        this.classList.add('selected');
        weatherInput.value = this.dataset.weather;
    });
});

// Update distance value display and map radius
const distanceSlider = document.getElementById('distance');
const distanceValue = document.getElementById('distanceValue');

function updateDistance(value) {
    distanceValue.textContent = Math.round(value);
    
    if (radiusCircle) {
        radiusCircle.setRadius(value * 1609.34);
        updateDistanceControl();
    }
}

distanceSlider.addEventListener('input', (e) => {
    updateDistance(e.target.value);
});

// Interactive distance ring functionality
function createDistanceControl() {
    if (distanceControl) {
        document.body.removeChild(distanceControl);
    }
    if (distanceLabel) {
        document.body.removeChild(distanceLabel);
    }
    
    // Create draggable control
    distanceControl = document.createElement('div');
    distanceControl.className = 'distance-control';
    distanceControl.innerHTML = '↔';
    distanceControl.style.display = 'none';
    document.body.appendChild(distanceControl);
    
    // Create distance label
    distanceLabel = document.createElement('div');
    distanceLabel.className = 'distance-label';
    distanceLabel.style.display = 'none';
    document.body.appendChild(distanceLabel);
    
    let isDragging = false;
    let startX, startY, startRadius;
    
    distanceControl.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        startRadius = Math.min(200, parseFloat(distanceSlider.value));
        distanceControl.style.cursor = 'grabbing';
        e.preventDefault();
        e.stopPropagation();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        const delta = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        
        // Determine direction of movement
        const angle = Math.atan2(deltaY, deltaX);
        const radiusChange = delta * Math.cos(angle) * 0.3; // More precise calculation
        
        const newRadius = Math.max(1, Math.min(200, startRadius + radiusChange));
        
        distanceSlider.value = newRadius;
        updateDistance(newRadius);
    });
    
    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            distanceControl.style.cursor = 'grab';
        }
    });
}

function updateDistanceControl() {
    if (!radiusCircle || !distanceControl || !distanceLabel) return;
    
    const center = radiusCircle.getLatLng();
    const radius = radiusCircle.getRadius();
    
    // Calculate the position on the edge of the circle (east direction)
    const edgeLat = center.lat;
    const edgeLng = center.lng + (radius / (111320 * Math.cos(center.lat * Math.PI / 180)));
    
    // Convert to pixel coordinates
    const centerPoint = map.latLngToContainerPoint(center);
    const edgePoint = map.latLngToContainerPoint([edgeLat, edgeLng]);
    
    // Position the control on the edge
    distanceControl.style.left = (edgePoint.x - 10) + 'px';
    distanceControl.style.top = (edgePoint.y - 10) + 'px';
    distanceControl.style.display = 'block';
    
    // Update distance label
    const labelX = edgePoint.x + 15;
    const labelY = edgePoint.y - 10;
    distanceLabel.style.left = labelX + 'px';
    distanceLabel.style.top = labelY + 'px';
    distanceLabel.textContent = Math.round(distanceSlider.value) + ' miles';
    distanceLabel.style.display = 'block';
}

// Create distance control on page load
createDistanceControl();

// Update control position when map moves
map.on('move', updateDistanceControl);
map.on('zoom', updateDistanceControl);

// Location autocomplete functionality
const fromInput = document.getElementById('from');
const suggestionsDiv = document.getElementById('locationSuggestions');
let timeoutId;

fromInput.addEventListener('input', function() {
    clearTimeout(timeoutId);
    const query = this.value.trim();
    
    if (query.length < 2) {
        suggestionsDiv.style.display = 'none';
        return;
    }

    timeoutId = setTimeout(() => {
        fetch(`/location-suggest?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(suggestions => {
                suggestionsDiv.innerHTML = '';
                if (suggestions.length > 0) {
                    suggestions.forEach(suggestion => {
                        const div = document.createElement('div');
                        div.className = 'suggestion-item';
                        div.textContent = suggestion.display_name;
                        div.addEventListener('click', () => {
                            fromInput.value = suggestion.display_name;
                            suggestionsDiv.style.display = 'none';
                            // Update map with selected location
                            updateMapLocation({
                                lat: parseFloat(suggestion.lat),
                                lon: parseFloat(suggestion.lon)
                            });
                        });
                        suggestionsDiv.appendChild(div);
                    });
                    suggestionsDiv.style.display = 'block';
                } else {
                    suggestionsDiv.style.display = 'none';
                }
            });
    }, 300);
});

// Hide suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!fromInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.style.display = 'none';
    }
});

// Update map with selected location
function updateMapLocation(coordinates) {
    // Remove existing radius circle and start point marker
    if (radiusCircle) {
        map.removeLayer(radiusCircle);
    }
    if (startPointMarker) {
        map.removeLayer(startPointMarker);
    }

    // Create start point marker
    const startIcon = L.divIcon({
        className: 'start-point-marker',
        html: '<div style="background-color: #3B82F6; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });

    startPointMarker = L.marker([coordinates.lat, coordinates.lon], {
        icon: startIcon
    }).addTo(map);

    // Create radius circle
    radiusCircle = L.circle([coordinates.lat, coordinates.lon], {
        radius: distanceSlider.value * 1609.34,
        color: '#3B82F6',
        fillColor: '#93C5FD',
        fillOpacity: 0.2,
        weight: 2
    }).addTo(map);

    map.setView([coordinates.lat, coordinates.lon], 8);
    
    // Update distance control position
    setTimeout(updateDistanceControl, 100);
}

// Handle form submission
const searchForm = document.getElementById('searchForm');

searchForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = {
        from: fromInput.value,
        weather: weatherInput.value,
        date: document.getElementById('date').value,
        distance: distanceSlider.value
    };

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '';
        // Remove old markers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];

        if (data.length === 0) {
            resultsDiv.innerHTML = '<p class="text-center text-gray-500">No destinations found matching your criteria.</p>';
            return;
        }

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
                    </div>
                    <div class="flex flex-col items-center justify-center">
                        <div class="weather-icon-result mb-1">
                            <img src="/weather-icons/${destination.weather.icon_code}.png" 
                                 alt="${destination.weather.condition}" 
                                 class="w-12 h-12">
                        </div>
                        <p class="text-sm text-gray-600 mt-1">${destination.weather.condition}</p>
                        <p class="text-sm font-semibold">${destination.weather.temperature.average}°C</p>
                    </div>
                </div>
            `;
            resultsDiv.appendChild(card);

            // Create custom icon for the marker with a visible background
            const weatherIcon = new WeatherIcon({
                iconUrl: `/weather-icons/${destination.weather.icon_code}.png`,
                className: 'weather-marker-icon'
            });

            // Create marker with custom icon
            const marker = L.marker([destination.coordinates.lat, destination.coordinates.lon], {
                icon: weatherIcon
            })
            .addTo(map)
            .bindPopup(`
                <div class="text-center">
                    <div class="weather-icon-result inline-block mb-2">
                        <img src="/weather-icons/${destination.weather.icon_code}.png" 
                             alt="${destination.weather.condition}" 
                             class="w-8 h-8">
                    </div>
                    <strong>${destination.index}. ${destination.city}</strong><br>
                    ${destination.region}, ${destination.country}<br>
                    ${destination.weather.condition}<br>
                    ${destination.weather.temperature.average}°C
                </div>
            `);
            markers.push(marker);

            // Add click event to card to pan/zoom to marker and open popup
            card.addEventListener('click', () => {
                map.setView([destination.coordinates.lat, destination.coordinates.lon], 10, { animate: true });
                marker.openPopup();
            });
        });
    })
    .catch(error => {
        console.error('Error:', error);
        resultsDiv.innerHTML = '<p class="text-center text-red-500">An error occurred while searching for destinations.</p>';
    });
});