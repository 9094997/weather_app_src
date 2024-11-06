// static/js/main.js
// Initialize the map
const map = L.map('map').setView([46.2276, 2.2137], 6); // Center on France

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Store markers and circle
let markers = [];
let radiusCircle = null;

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

    // Debounce the API call
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

                // Add click handlers to suggestions
                document.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        fromInput.value = item.textContent.trim();
                        suggestionsDiv.style.display = 'none';
                        
                        // Update map with selected location
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
    }, 300); // 300ms delay
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
        color: 'blue',
        fillColor: '#30c',
        fillOpacity: 0.1
    }).addTo(map);

    map.setView([coordinates.lat, coordinates.lon], 8);
}

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

// Handle form submission
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        from: fromInput.value,
        weather: document.getElementById('weather').value,
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
            resultsDiv.innerHTML += `
                <div class="p-4 bg-gray-50 rounded-lg shadow">
                    <h3 class="font-bold text-lg text-gray-800">${destination.city}</h3>
                    <p class="text-gray-600">${destination.description}</p>
                    <p class="text-sm text-gray-500 mt-2">Distance: ${destination.distance} miles</p>
                </div>
            `;

            if (destination.coordinates) {
                const marker = L.marker([destination.coordinates.lat, destination.coordinates.lon])
                    .bindPopup(`<b>${destination.city}</b><br>${destination.description}`)
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
        document.getElementById('results').innerHTML = `
            <div class="p-4 bg-red-100 text-red-700 rounded-lg">
                An error occurred while searching for destinations.
            </div>
        `;
    }
});