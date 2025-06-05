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

// Set up date restrictions
function setupDateRestrictions() {
    const dateInput = document.getElementById('date');
    const today = new Date();
    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 4); // Limit to 4 days as per weather API
    
    // Format dates as YYYY-MM-DD
    const formatDate = (date) => {
        const d = new Date(date);
        const month = (d.getMonth() + 1).toString().padStart(2, '0');
        const day = d.getDate().toString().padStart(2, '0');
        return `${d.getFullYear()}-${month}-${day}`;
    };
    
    // Set min and max dates
    dateInput.min = formatDate(today);
    dateInput.max = formatDate(maxDate);
    
    // Set default value to today
    dateInput.value = formatDate(today);
}

// Call setup function when page loads
setupDateRestrictions();

// Weather icon selection
const weatherIcons = document.querySelectorAll('.weather-icon');
const weatherInput = document.getElementById('weather');

weatherIcons.forEach(icon => {
    icon.addEventListener('click', (e) => {
        weatherIcons.forEach(i => i.classList.remove('selected'));
        icon.classList.add('selected');
        weatherInput.value = icon.dataset.weather;
    });
});

// Update distance value display and map radius
const distanceSlider = document.getElementById('distance');
const distanceValue = document.getElementById('distanceValue');

function updateDistance(value) {
    distanceValue.textContent = value;
    
    if (radiusCircle) {
        radiusCircle.setRadius(value * 1609.34);
    }
}

distanceSlider.addEventListener('input', (e) => {
    updateDistance(e.target.value);
});

// Location autocomplete functionality
const fromInput = document.getElementById('from');
const suggestionsDiv = document.getElementById('locationSuggestions');
let debounceTimer;

fromInput.addEventListener('input', async (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value;
    
    if (query.length < 2) {
        suggestionsDiv.style.display = 'none';
        return;
    }

    debounceTimer = setTimeout(async () => {
        try {
            const response = await fetch(`/location-suggest?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();
            
            if (suggestions.length > 0) {
                suggestionsDiv.innerHTML = suggestions.map(place => `
                    <div class="suggestion-item" data-lat="${place.lat}" data-lon="${place.lon}">
                        ${place.display_name}
                    </div>
                `).join('');
                suggestionsDiv.style.display = 'block';

                document.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        fromInput.value = item.textContent.trim();
                        suggestionsDiv.style.display = 'none';
                        
                        updateMapLocation({
                            lat: parseFloat(item.dataset.lat),
                            lon: parseFloat(item.dataset.lon)
                        });
                    });
                });
            } else {
                suggestionsDiv.style.display = 'none';
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
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
    if (radiusCircle) {
        map.removeLayer(radiusCircle);
    }

    radiusCircle = L.circle([coordinates.lat, coordinates.lon], {
        radius: distanceSlider.value * 1609.34,
        color: '#3B82F6',
        fillColor: '#93C5FD',
        fillOpacity: 0.2
    }).addTo(map);

    map.setView([coordinates.lat, coordinates.lon], 8);
}

// Handle form submission
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        from: fromInput.value,
        weather: weatherInput.value,
        date: document.getElementById('date').value,
        distance: document.getElementById('distance').value
    };

    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '';

        // Clear existing markers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];
        
        if (data.error) {
            resultsDiv.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded-lg">
                Error: ${data.error}
            </div>`;
            return;
        }

        if (data.length === 0) {
            resultsDiv.innerHTML = `<div class="p-4 bg-yellow-100 text-yellow-700 rounded-lg">
                No destinations found matching your criteria.
            </div>`;
            return;
        }

        data.forEach(destination => {
            const weatherInfo = destination.weather;
            const temp = weatherInfo.temperature;
            
            resultsDiv.innerHTML += `
                <div class="p-4 bg-gray-50 rounded-lg shadow hover:shadow-md transition-shadow">
                    <h3 class="font-bold text-lg text-gray-800">${destination.city}, ${destination.region}</h3>
                    <div class="mt-2">
                        <p class="text-gray-600">
                            <i class="fas fa-temperature-high mr-2"></i>
                            Temperature: ${temp.average}°C (Max: ${temp.max}°C, Min: ${temp.min}°C)
                        </p>
                        <p class="text-gray-600">
                            <i class="fas fa-cloud mr-2"></i>
                            Condition: ${weatherInfo.condition}
                        </p>
                    </div>
                    <p class="text-sm text-gray-500 mt-2">Distance: ${destination.distance} miles</p>
                </div>
            `;

            if (destination.coordinates) {
                const marker = L.marker([destination.coordinates.lat, destination.coordinates.lon])
                    .bindPopup(`
                        <b>${destination.city}</b><br>
                        Temperature: ${temp.average}°C<br>
                        Condition: ${weatherInfo.condition}
                    `)
                    .addTo(map);
                markers.push(marker);
            }
        });

        if (markers.length > 0) {
            const group = L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
        }
    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded-lg">
            An error occurred while searching for destinations.
        </div>`;
    }
});