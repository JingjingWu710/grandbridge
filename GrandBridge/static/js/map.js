// Enhanced Food Map JavaScript

class FoodMapManager {
    constructor(isAdmin) {
        this.isAdmin = isAdmin;
        this.map = null;
        this.markers = [];
        this.userMarker = null;
        this.selectedLocation = null;
        this.allLocations = [];
        this.searchCircle = null;
        this.infoWindow = null;
        this.directionsService = null;
        this.directionsRenderer = null;
    }

    init() {
        // Initialize map with Cardiff coordinates
        this.map = new google.maps.Map(document.getElementById('map'), {
            zoom: 12,
            center: { lat: 51.4816, lng: -3.1791 },
            styles: this.getMapStyles(),
            mapTypeControl: true,
            streetViewControl: true,
            fullscreenControl: true
        });

        // Initialize services
        this.infoWindow = new google.maps.InfoWindow();
        this.directionsService = new google.maps.DirectionsService();
        this.directionsRenderer = new google.maps.DirectionsRenderer();
        this.directionsRenderer.setMap(this.map);

        // Set up search boxes
        this.setupSearchBoxes();
        
        // Load locations
        this.loadLocations();
        
        // Set up event listeners
        this.setupEventListeners();
    }

    getMapStyles() {
        return [
            {
                featureType: "poi.business",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            },
            {
                featureType: "water",
                elementType: "geometry",
                stylers: [{ color: "#a2daf2" }]
            },
            {
                featureType: "landscape.man_made",
                elementType: "geometry",
                stylers: [{ color: "#f7f1df" }]
            },
            {
                featureType: "landscape.natural",
                elementType: "geometry",
                stylers: [{ color: "#d0e3b4" }]
            }
        ];
    }

    setupSearchBoxes() {
        if (this.isAdmin) {
            const adminSearchBox = new google.maps.places.SearchBox(
                document.getElementById('admin-search-box')
            );
            
            adminSearchBox.addListener('places_changed', () => {
                const places = adminSearchBox.getPlaces();
                if (places.length > 0) {
                    const place = places[0];
                    this.map.setCenter(place.geometry.location);
                    this.map.setZoom(15);
                    
                    // Auto-fill address
                    document.getElementById('location-address').value = 
                        place.formatted_address || '';
                }
            });
        }
        
        const userSearchBox = new google.maps.places.SearchBox(
            document.getElementById('user-search-box')
        );
        
        userSearchBox.addListener('places_changed', () => {
            const places = userSearchBox.getPlaces();
            if (places.length > 0) {
                this.updateUserLocation(places[0].geometry.location);
            }
        });
    }

    setupEventListeners() {
        // Radius change listener
        document.querySelectorAll('input[name="radius"]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (this.userMarker) {
                    this.searchNearbyLocations();
                }
            });
        });

        // Map click listener for admin
        if (this.isAdmin) {
            this.map.addListener('click', (event) => {
                this.showAddLocationDialog(event.latLng);
            });
        }
    }

    loadLocations() {
        fetch('/foodmap/get_locations')
            .then(response => response.json())
            .then(data => {
                this.allLocations = data;
                this.displayMarkers(data);
                this.updateLocationCount(data.length);
            })
            .catch(error => {
                console.error('Error loading locations:', error);
                this.showNotification('Failed to load locations', 'error');
            });
    }

    displayMarkers(locations) {
        // Clear existing markers
        this.clearMarkers();
        
        // Create marker clusterer for better performance with many markers
        const markerCluster = [];
        
        locations.forEach(location => {
            const marker = new google.maps.Marker({
                position: { lat: location.lat, lng: location.lng },
                map: this.map,
                title: location.name || 'Food Pickup Point',
                icon: this.getMarkerIcon(location),
                animation: google.maps.Animation.DROP
            });
            
            // Add info window
            marker.addListener('click', () => {
                this.showLocationInfo(location, marker);
            });
            
            // Double click for details
            marker.addListener('dblclick', () => {
                this.showLocationDetails(location);
            });
            
            this.markers.push(marker);
            markerCluster.push(marker);
        });

        // Add marker clusterer if many locations
        if (locations.length > 20) {
            new MarkerClusterer(this.map, markerCluster, {
                imagePath: 'https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m'
            });
        }
    }

    getMarkerIcon(location) {
        // Custom icons based on location properties
        const baseUrl = 'http://maps.google.com/mapfiles/ms/icons/';
        
        if (!location.is_active) {
            return baseUrl + 'grey-dot.png';
        } else if (location.capacity && location.capacity.includes('100+')) {
            return baseUrl + 'red-dot.png';
        } else {
            return {
                url: baseUrl + 'green-dot.png',
                scaledSize: new google.maps.Size(40, 40)
            };
        }
    }

    showLocationInfo(location, marker) {
        const content = `
            <div style="padding: 10px; max-width: 300px;">
                <h4 style="color: #2c6f4f; margin: 0 0 10px 0;">
                    ${location.name}
                </h4>
                <p style="margin: 5px 0;">
                    <strong>📍 Address:</strong><br>
                    ${location.address || 'Not specified'}
                </p>
                ${location.operating_hours ? `
                    <p style="margin: 5px 0;">
                        <strong>🕐 Hours:</strong> ${location.operating_hours}
                    </p>
                ` : ''}
                ${location.distance ? `
                    <p style="margin: 5px 0;">
                        <strong>📏 Distance:</strong> ${location.distance.toFixed(1)} km
                    </p>
                ` : ''}
                <div style="margin-top: 10px;">
                    <button onclick="foodMap.showLocationDetails(${JSON.stringify(location).replace(/"/g, '&quot;')})" 
                            class="btn btn-sm btn-primary">
                        View Details
                    </button>
                    <button onclick="foodMap.getDirections(${location.lat}, ${location.lng})" 
                            class="btn btn-sm btn-success">
                        Get Directions
                    </button>
                </div>
            </div>
        `;
        
        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker);
    }

    clearMarkers() {
        this.markers.forEach(marker => marker.setMap(null));
        this.markers = [];
    }

    updateUserLocation(location) {
        // Remove existing user marker
        if (this.userMarker) {
            this.userMarker.setMap(null);
        }
        
        // Add new user marker with custom icon
        this.userMarker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: 'Your Location',
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 10,
                fillColor: '#4285F4',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2
            },
            animation: google.maps.Animation.DROP
        });
        
        // Add accuracy circle
        new google.maps.Circle({
            strokeColor: '#4285F4',
            strokeOpacity: 0.3,
            strokeWeight: 1,
            fillColor: '#4285F4',
            fillOpacity: 0.1,
            map: this.map,
            center: location,
            radius: 50 // 50 meters accuracy
        });
        
        this.map.setCenter(location);
        this.map.setZoom(14);
    }

    searchNearbyLocations() {
        if (!this.userMarker) {
            this.showNotification('Please set your location first', 'warning');
            return;
        }
        
        const userPos = this.userMarker.getPosition();
        const radius = parseFloat(document.querySelector('input[name="radius"]:checked').value);
        
        // Visual feedback with search circle
        this.drawSearchCircle(userPos, radius);
        
        // Make API call for nearby locations
        fetch('/foodmap/get_nearby_locations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: userPos.lat(),
                lng: userPos.lng(),
                radius: radius
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.displayLocationCards(data.locations);
                this.highlightNearbyMarkers(data.locations);
                
                // Show summary
                this.showNotification(
                    `Found ${data.total} location(s) within ${radius}km`,
                    'success'
                );
            }
        })
        .catch(error => {
            console.error('Error searching locations:', error);
            this.showNotification('Search failed', 'error');
        });
    }

    drawSearchCircle(center, radius) {
        if (this.searchCircle) {
            this.searchCircle.setMap(null);
        }
        
        this.searchCircle = new google.maps.Circle({
            strokeColor: '#4a7c59',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: '#e8f5e9',
            fillOpacity: 0.2,
            map: this.map,
            center: center,
            radius: radius * 1000,
            clickable: false
        });
        
        // Fit map to circle bounds
        this.map.fitBounds(this.searchCircle.getBounds());
    }

    highlightNearbyMarkers(nearbyLocations) {
        const nearbyIds = nearbyLocations.map(loc => loc.id);
        
        this.markers.forEach((marker, index) => {
            if (this.allLocations[index]) {
                const isNearby = nearbyIds.includes(this.allLocations[index].id);
                marker.setAnimation(isNearby ? google.maps.Animation.BOUNCE : null);
                
                // Stop animation after 2 seconds
                if (isNearby) {
                    setTimeout(() => marker.setAnimation(null), 2000);
                }
            }
        });
    }

    getDirections(lat, lng) {
        if (!this.userMarker) {
            // Open in Google Maps directly
            const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
            window.open(url, '_blank');
            return;
        }
        
        // Show directions on map
        const request = {
            origin: this.userMarker.getPosition(),
            destination: { lat: lat, lng: lng },
            travelMode: google.maps.TravelMode.DRIVING
        };
        
        this.directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                this.directionsRenderer.setDirections(result);
            } else {
                this.showNotification('Could not calculate directions', 'error');
            }
        });
    }

    showAddLocationDialog(latLng) {
        const geocoder = new google.maps.Geocoder();
        
        geocoder.geocode({ location: latLng }, (results, status) => {
            if (status === 'OK' && results[0]) {
                const address = results[0].formatted_address;
                
                // Fill in the admin form
                document.getElementById('admin-search-box').value = address;
                document.getElementById('location-address').value = address;
                
                // Scroll to form
                document.querySelector('.admin-panel').scrollIntoView({ 
                    behavior: 'smooth' 
                });
            }
        });
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} notification`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 250px;
            animation: slideIn 0.3s ease;
        `;
        notification.innerHTML = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    updateLocationCount(count) {
        const countElement = document.getElementById('location-count');
        if (countElement) {
            countElement.textContent = count;
        }
    }
}

// Initialize map when page loads
let foodMap;

function initMap() {
    foodMap = new FoodMapManager(isAdmin);
    foodMap.init();
}

// Global functions for HTML onclick handlers
function useCurrentLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
                const pos = new google.maps.LatLng(
                    position.coords.latitude,
                    position.coords.longitude
                );
                foodMap.updateUserLocation(pos);
            },
            error => {
                console.error('Geolocation error:', error);
                foodMap.showNotification('Unable to get your location', 'error');
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );
    } else {
        foodMap.showNotification('Geolocation is not supported', 'error');
    }
}

function searchNearbyLocations() {
    foodMap.searchNearbyLocations();
}

function showAllLocations() {
    foodMap.displayLocationCards(foodMap.allLocations);
    foodMap.displayMarkers(foodMap.allLocations);
    
    if (foodMap.searchCircle) {
        foodMap.searchCircle.setMap(null);
    }
    
    // Fit map to show all markers
    if (foodMap.markers.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        foodMap.markers.forEach(marker => bounds.extend(marker.getPosition()));
        foodMap.map.fitBounds(bounds);
    }
}

function displayLocationCards(locations) {
    foodMap.displayLocationCards(locations);
}

function showLocationDetails(location) {
    foodMap.selectedLocation = location;
    // Update modal and show it
    // Modal code would be here
    $('#locationModal').modal('show');
}