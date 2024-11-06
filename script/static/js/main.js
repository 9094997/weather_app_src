// static/js/main.js
// Initialize the map
const map = L.map('map').setView([46.2276, 2.2137], 6); // Center on France

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Store markers and circle
let markers = [];
let radiusCircle = null;

// Update distance value display and map radius
const distanceSlider = document.getElementById('distance');
const distanceValue = document.getElementById('distanceValue');

function updateDistance(value) {
    // Update display value
    distanceValue.textContent = value;
    
    // Update map circle if we have a starting point
    const fromInput = document.getElementById('from').value;
    if (fromInput && radiusCircle) {
        radiusCircle.setRadius(value * 1609.34); // Convert miles to meters
    }
}

// Listen for slider input
distanceSlider.addEventListener('input', (e) => {
    updateDistance(e.target.value);
});

// Handle form submission
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        from: document.getElementById('from').value,
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
        markers.forEach(marker => map.removeMarker(marker));
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

        // Add markers for matching destinations
        data.forEach(destination => {
            resultsDiv.innerHTML += `
                <div class="p-4 bg-gray-50 rounded-lg shadow">
                    <h3 class="font-bold text-lg text-gray-800">${destination.city}</h3>
                    <p class="text-gray-600">${destination.description}</p>
                    <p class="text-sm text-gray-500 mt-2">Distance: ${destination.distance} miles</p>
                </div>
            `;

            // Add marker to map
            if (destination.coordinates) {
                const marker = L.marker([destination.coordinates.lat, destination.coordinates.lon])
                    .bindPopup(`<b>${destination.city}</b><br>${destination.description}`)
                    .addTo(map);
                markers.push(marker);
            }
        });

        // Update map view to include all markers
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

// Update map when "From" location changes
document.getElementById('from').addEventListener('change', async (e) => {
    const location = e.target.value;
    if (!location) return;

    try {
        // Get coordinates for the location (you'll need to implement this endpoint)
        const response = await fetch(`/geocode?location=${encodeURIComponent(location)}`);
        const data = await response.json();

        if (data.coordinates) {
            // Clear existing circle
            if (radiusCircle) {
                map.removeLayer(radiusCircle);
            }

            // Add new circle
            radiusCircle = L.circle([data.coordinates.lat, data.coordinates.lon], {
                radius: distanceSlider.value * 1609.34, // Convert miles to meters
                color: 'blue',
                fillColor: '#30c',
                fillOpacity: 0.1
            }).addTo(map);

            // Center map on location
            map.setView([data.coordinates.lat, data.coordinates.lon], 8);
        }
    } catch (error) {
        console.error('Error getting coordinates:', error);
    }
});