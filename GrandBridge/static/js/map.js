// Enhanced Food Map JavaScript

class FoodMapManager {
    constructor(isAdmin) {
        this.isAdmin = isAdmin;
        this.adminModeActive = false;
        this.map = null;
        this.markers = [];
        this.userMarker = null;
        this.selectedLocation = null;
        this.selectedPlace = null;
        this.allLocations = [];
        this.searchCircle = null;
        this.infoWindow = null;
        this.directionsService = null;
        this.directionsRenderer = null;
        this.adminAutocomplete = null;
        this.userAutocomplete = null;
        this.tempMarker = null;
    }

    init() {
        console.log('Initializing map...');
        
        // Initialize map with Cardiff coordinates
        this.map = new google.maps.Map(document.getElementById('map'), {
            zoom: 12,
            center: { lat: 51.4816, lng: -3.1791 },
            styles: this.getMapStyles(),
            mapTypeControl: true,
            mapTypeControlOptions: {
                style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
                position: google.maps.ControlPosition.TOP_RIGHT
            },
            streetViewControl: true,
            fullscreenControl: true
        });

        // Initialize services
        this.infoWindow = new google.maps.InfoWindow();
        this.directionsService = new google.maps.DirectionsService();
        this.directionsRenderer = new google.maps.DirectionsRenderer();
        this.directionsRenderer.setMap(this.map);

        // Set up autocomplete
        this.setupAutocomplete();
        
        // Load locations from database
        this.loadLocations();
        
        // Set up event listeners
        this.setupEventListeners();
    }

    getMapStyles() {
        return [
            {
                featureType: "poi",
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

    setupAutocomplete() {
        console.log('Setting up autocomplete...');
        
        // Setup admin autocomplete only if user is admin
        if (this.isAdmin) {
            const adminSearchBox = document.getElementById('admin-search-box');
            if (adminSearchBox) {
                this.adminAutocomplete = new google.maps.places.Autocomplete(adminSearchBox, {
                    types: ['establishment', 'geocode'],
                    componentRestrictions: { country: 'gb' },
                    fields: ['name', 'geometry', 'formatted_address', 'place_id']
                });
                
                this.adminAutocomplete.addListener('place_changed', () => {
                    const place = this.adminAutocomplete.getPlace();
                    console.log('Admin place selected:', place);
                    
                    if (place.geometry) {
                        this.selectedPlace = place;
                        
                        // Center map on selected place
                        this.map.setCenter(place.geometry.location);
                        this.map.setZoom(15);
                        
                        // Auto-fill address field
                        const addressField = document.getElementById('location-address');
                        if (addressField) {
                            addressField.value = place.formatted_address || '';
                        }
                        
                        // Add temporary marker
                        this.addTemporaryMarker(place.geometry.location);
                    }
                });
            }
        }
        
        // Setup user autocomplete
        const userSearchBox = document.getElementById('user-search-box');
        if (userSearchBox) {
            this.userAutocomplete = new google.maps.places.Autocomplete(userSearchBox, {
                types: ['geocode'],
                componentRestrictions: { country: 'gb' },
                fields: ['geometry', 'formatted_address']
            });
            
            this.userAutocomplete.addListener('place_changed', () => {
                const place = this.userAutocomplete.getPlace();
                console.log('User place selected:', place);
                
                if (place.geometry) {
                    this.updateUserLocation(place.geometry.location);
                }
            });
        }
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

        // Close modal when clicking outside
        window.onclick = (event) => {
            const modal = document.getElementById('locationModal');
            if (event.target === modal) {
                this.closeModal();
            }
        };

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Press ESC to close modal
            if (e.key === 'Escape') {
                this.closeModal();
            }
            
            // Ctrl+Shift+A to toggle admin mode (only for admins)
            if (e.ctrlKey && e.shiftKey && e.key === 'A' && this.isAdmin) {
                this.toggleAdminMode();
            }
        });
    }

    addTemporaryMarker(location) {
        // Remove existing temporary marker
        if (this.tempMarker) {
            this.tempMarker.setMap(null);
        }
        
        // Add new temporary marker
        this.tempMarker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: 'New Location',
            icon: {
                url: 'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
                scaledSize: new google.maps.Size(40, 40)
            },
            animation: google.maps.Animation.BOUNCE
        });
        
        // Stop bouncing after 2 seconds
        setTimeout(() => {
            if (this.tempMarker) {
                this.tempMarker.setAnimation(null);
            }
        }, 2000);
    }

    loadLocations() {
        console.log('Loading locations from database...');
        
        fetch('/foodmap/get_locations')
            .then(response => response.json())
            .then(data => {
                if (Array.isArray(data)) {
                    this.allLocations = data;
                    this.updateLocationCount(this.allLocations.length);
                    this.displayMarkers(this.allLocations);
                    this.displayLocationCards(this.allLocations);
                } else {
                    console.error('Invalid response format:', data);
                    this.showNotification('Failed to load locations', 'error');
                }
            })
            .catch(error => {
                console.error('Error loading locations:', error);
                this.showNotification('Failed to load locations', 'error');
            });
    }

    displayMarkers(locations) {
        console.log('Displaying markers for', locations.length, 'locations');
        
        // Clear existing markers
        this.clearMarkers();
        
        if (!locations || locations.length === 0) {
            console.log('No locations to display');
            return;
        }
        
        const bounds = new google.maps.LatLngBounds();
        
        locations.forEach((location, index) => {
            const lat = parseFloat(location.lat);
            const lng = parseFloat(location.lng);
            
            if (isNaN(lat) || isNaN(lng)) {
                console.error('Invalid coordinates for location:', location);
                return;
            }
            
            const marker = new google.maps.Marker({
                position: { lat: lat, lng: lng },
                map: this.map,
                title: location.name || 'Food Pickup Point',
                icon: this.getMarkerIcon(location)
            });
            
            // Stagger the drop animation
            setTimeout(() => {
                marker.setAnimation(google.maps.Animation.DROP);
            }, index * 100);
            
            // Add click listener for info window
            marker.addListener('click', () => {
                this.showMarkerInfo(location, marker);
            });
            
            this.markers.push(marker);
            bounds.extend(marker.getPosition());
        });
        
        // Fit bounds to show all markers
        if (this.markers.length > 0) {
            this.map.fitBounds(bounds);
            
            // Don't zoom in too much for single marker
            if (this.markers.length === 1) {
                setTimeout(() => {
                    this.map.setZoom(Math.min(this.map.getZoom(), 14));
                }, 100);
            }
        }
    }

    getMarkerIcon(location) {
        // Default green marker
        return {
            url: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
            scaledSize: new google.maps.Size(35, 35)
        };
    }

    clearMarkers() {
        this.markers.forEach(marker => marker.setMap(null));
        this.markers = [];
    }

    showMarkerInfo(location, marker) {
        const content = `
            <div style="padding: 10px; max-width: 300px;">
                <h4 style="color: #2c6f4f; margin: 0 0 10px 0;">
                    ${location.name || 'Food Pickup Point'}
                </h4>
                <p style="margin: 5px 0;">
                    <strong>📍 Address:</strong><br>
                    ${location.address || 'Address not specified'}
                </p>
                ${location.distance ? `
                    <p style="margin: 5px 0;">
                        <strong>📏 Distance:</strong> ${location.distance.toFixed(1)} km
                    </p>
                ` : ''}
                <div style="margin-top: 10px;">
                    <button onclick="foodMap.showLocationDetails(${location.id})" 
                            style="background: #4a7c59; color: white; border: none; padding: 5px 10px; border-radius: 5px; margin-right: 5px; cursor: pointer;">
                        View Details
                    </button>
                    <button onclick="foodMap.getDirectionsToLocation(${location.lat}, ${location.lng})" 
                            style="background: #28a745; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;">
                        Directions
                    </button>
                </div>
            </div>
        `;
        
        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker);
    }

    displayLocationCards(locations) {
        console.log('Displaying location cards for', locations.length, 'locations');
        
        const container = document.getElementById('location-cards');
        if (!container) {
            console.error('Location cards container not found');
            return;
        }
        
        container.innerHTML = '';
        
        if (!locations || locations.length === 0) {
            container.innerHTML = '<div class="info-box">No food pickup points found. Try adjusting your search radius or check back later!</div>';
            return;
        }
        
        locations.forEach(location => {
            const card = document.createElement('div');
            card.className = 'location-card';
            
            card.innerHTML = `
                <h4 style="color: #2c6f4f;">
                    ${location.name || 'Food Pickup Point'}
                    ${location.distance !== undefined ? `<span class="distance-badge">${location.distance.toFixed(1)} km away</span>` : ''}
                </h4>
                <p style="font-size: 1.1rem; margin: 10px 0;">
                    <strong>📍 Address:</strong> ${location.address || 'Address not specified'}
                </p>
                <button onclick="foodMap.showLocationDetails(${location.id})" 
                        class="btn-custom btn-primary-custom">
                    View Details
                </button>
                <button onclick="foodMap.centerOnLocation(${location.lat}, ${location.lng})" 
                        class="btn-custom btn-secondary-custom">
                    Show on Map
                </button>
            `;
            container.appendChild(card);
        });
    }

    updateLocationCount(count) {
        const countElement = document.getElementById('location-count');
        if (countElement) {
            countElement.textContent = count;
        }
    }

    updateUserLocation(location) {
        // Remove existing user marker
        if (this.userMarker) {
            this.userMarker.setMap(null);
        }
        
        // Add new user marker
        this.userMarker = new google.maps.Marker({
            position: location,
            map: this.map,
            title: 'Your Location',
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
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
            radius: 50
        });
        
        this.map.setCenter(location);
        this.map.setZoom(14);
    }

    searchNearbyLocations() {
        if (!this.userMarker) {
            this.showNotification('Please enter your location or use current location first.', 'warning');
            return;
        }
        
        const userPos = this.userMarker.getPosition();
        const radius = parseFloat(document.querySelector('input[name="radius"]:checked').value);
        
        console.log('Searching within', radius, 'km of', userPos.lat(), userPos.lng());
        
        // Draw search circle
        this.drawSearchCircle(userPos, radius);
        
        // Filter locations within radius
        const nearbyLocations = this.allLocations.filter(location => {
            const distance = this.calculateDistance(
                userPos.lat(), userPos.lng(),
                parseFloat(location.lat), parseFloat(location.lng)
            );
            location.distance = distance;
            return distance <= radius;
        });
        
        // Sort by distance
        nearbyLocations.sort((a, b) => a.distance - b.distance);
        
        console.log('Found', nearbyLocations.length, 'nearby locations');
        
        // Display results
        this.displayLocationCards(nearbyLocations);
        this.highlightNearbyMarkers(nearbyLocations);
        
        this.showNotification(`Found ${nearbyLocations.length} location(s) within ${radius}km`, 
            nearbyLocations.length > 0 ? 'success' : 'warning');
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
                if (isNearby) {
                    marker.setAnimation(google.maps.Animation.BOUNCE);
                    setTimeout(() => marker.setAnimation(null), 2000);
                }
            }
        });
    }

    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    showAllLocations() {
        console.log('Showing all locations');
        
        // Clear search circle if exists
        if (this.searchCircle) {
            this.searchCircle.setMap(null);
            this.searchCircle = null;
        }
        
        // Reset distance property for all locations
        this.allLocations.forEach(location => {
            delete location.distance;
        });
        
        // Display all locations
        this.displayLocationCards(this.allLocations);
        this.displayMarkers(this.allLocations);
        
        this.showNotification(`Showing all ${this.allLocations.length} locations`, 'info');
    }

    centerOnLocation(lat, lng) {
        lat = parseFloat(lat);
        lng = parseFloat(lng);
        this.map.setCenter({ lat: lat, lng: lng });
        this.map.setZoom(16);
        
        // Find and animate the marker
        this.markers.forEach(marker => {
            const pos = marker.getPosition();
            if (Math.abs(pos.lat() - lat) < 0.0001 && Math.abs(pos.lng() - lng) < 0.0001) {
                marker.setAnimation(google.maps.Animation.BOUNCE);
                setTimeout(() => marker.setAnimation(null), 2000);
                
                // Open info window for this marker
                const location = this.allLocations.find(loc => 
                    Math.abs(parseFloat(loc.lat) - lat) < 0.0001 && 
                    Math.abs(parseFloat(loc.lng) - lng) < 0.0001
                );
                if (location) {
                    this.showMarkerInfo(location, marker);
                }
            }
        });
    }

    showLocationDetails(locationId) {
        const location = this.allLocations.find(loc => loc.id === locationId);
        if (!location) {
            this.showNotification('Location not found', 'error');
            return;
        }
        
        this.selectedLocation = location;
        const modalContent = document.getElementById('modal-content');
        modalContent.innerHTML = `
            <h3 style="color: #2c6f4f;">${location.name || 'Food Pickup Point'}</h3>
            <div style="margin: 20px 0;">
                <p><strong>📍 Full Address:</strong></p>
                <p style="font-size: 1.2rem; background: #e8f5e9; padding: 15px; border-radius: 10px;">
                    ${location.address || 'Address not specified'}
                </p>
            </div>
            <div style="margin: 20px 0;">
                <p><strong>📐 Coordinates:</strong></p>
                <p>Latitude: ${parseFloat(location.lat).toFixed(6)}, Longitude: ${parseFloat(location.lng).toFixed(6)}</p>
            </div>
            ${location.distance !== undefined ? `
                <div style="margin: 20px 0;">
                    <p><strong>📏 Distance from you:</strong></p>
                    <p style="font-size: 1.3rem; color: #4a7c59;">${location.distance.toFixed(1)} km</p>
                </div>
            ` : ''}
        `;
        
        document.getElementById('locationModal').classList.add('show');
    }

    closeModal() {
        document.getElementById('locationModal').classList.remove('show');
    }

    getDirections() {
        if (this.selectedLocation) {
            this.getDirectionsToLocation(this.selectedLocation.lat, this.selectedLocation.lng);
        }
    }

    getDirectionsToLocation(lat, lng) {
        const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        window.open(url, '_blank');
    }

    showNotification(message, type = 'info') {
        // Remove any existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(notif => notif.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification alert-${type}`;
        notification.innerHTML = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Admin functions
    addLocationFromSearch() {
        if (!this.isAdmin) {
            this.showNotification('Admin access required', 'error');
            return;
        }
        
        const nameInput = document.getElementById('location-name');
        const addressInput = document.getElementById('location-address');
        
        if (!this.selectedPlace) {
            this.showNotification('Please search and select a location first.', 'warning');
            return;
        }
        
        if (!nameInput.value.trim()) {
            this.showNotification('Please provide a name for this location.', 'warning');
            nameInput.focus();
            return;
        }
        
        const newLocation = {
            lat: this.selectedPlace.geometry.location.lat(),
            lng: this.selectedPlace.geometry.location.lng(),
            name: nameInput.value.trim(),
            address: addressInput.value || this.selectedPlace.formatted_address
        };
        
        // Show loading
        this.showNotification('Adding location...', 'info');
        
        // Save to database via API
        fetch('/foodmap/save_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(newLocation)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.showNotification('Location added successfully!', 'success');
                this.clearAdminForm();
                
                // Remove temporary marker
                if (this.tempMarker) {
                    this.tempMarker.setMap(null);
                    this.tempMarker = null;
                }
                
                // Reload locations to show the new one
                this.loadLocations();
            } else {
                this.showNotification('Failed to add location: ' + (data.message || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showNotification('Failed to add location. Please try again.', 'error');
        });
    }

    clearAdminForm() {
        const adminSearchBox = document.getElementById('admin-search-box');
        const nameInput = document.getElementById('location-name');
        const addressInput = document.getElementById('location-address');
        
        if (adminSearchBox) adminSearchBox.value = '';
        if (nameInput) nameInput.value = '';
        if (addressInput) addressInput.value = '';
        
        this.selectedPlace = null;
        
        // Remove temporary marker
        if (this.tempMarker) {
            this.tempMarker.setMap(null);
            this.tempMarker = null;
        }
    }

    deleteCurrentLocation() {
        if (!this.isAdmin || !this.selectedLocation) {
            this.showNotification('Admin access required', 'error');
            return;
        }
        
        if (confirm(`Are you sure you want to delete "${this.selectedLocation.name || 'this location'}"?`)) {
            // Show loading
            this.showNotification('Deleting location...', 'info');
            
            // Delete from database via API
            fetch(`/foodmap/delete_location/${this.selectedLocation.id}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.showNotification('Location deleted successfully!', 'success');
                    this.closeModal();
                    // Reload locations to reflect the deletion
                    this.loadLocations();
                } else {
                    this.showNotification('Failed to delete location: ' + (data.message || 'Unknown error'), 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showNotification('Failed to delete location. Please try again.', 'error');
            });
        }
    }

    toggleAdminMode() {
        if (!this.isAdmin) {
            this.showNotification('Admin access required', 'error');
            return;
        }
        
        this.adminModeActive = !this.adminModeActive;
        const adminPanel = document.getElementById('admin-panel');
        
        if (this.adminModeActive) {
            adminPanel.style.display = 'block';
            this.showNotification('Admin mode enabled', 'success');
            
            // Re-initialize autocomplete for admin if needed
            if (!this.adminAutocomplete) {
                this.setupAutocomplete();
            }
        } else {
            adminPanel.style.display = 'none';
            this.showNotification('Admin mode disabled', 'info');
            
            // Clear admin form when disabling admin mode
            this.clearAdminForm();
        }
    }
}

// Initialize map when page loads
let foodMap;

function initMap() {
    // Get isAdmin value from the template (should be set in the HTML)
    const isAdminValue = typeof isAdmin !== 'undefined' ? isAdmin : false;
    foodMap = new FoodMapManager(isAdminValue);
    foodMap.init();
}

// Global functions for HTML onclick handlers
function useCurrentLocation() {
    if (navigator.geolocation) {
        foodMap.showNotification('Getting your location...', 'info');
        
        navigator.geolocation.getCurrentPosition(
            position => {
                const pos = new google.maps.LatLng(
                    position.coords.latitude,
                    position.coords.longitude
                );
                foodMap.updateUserLocation(pos);
                foodMap.showNotification('Location found!', 'success');
            },
            error => {
                console.error('Geolocation error:', error);
                let errorMessage = 'Unable to get your location.';
                
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = 'Location permission denied. Please enable location access.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = 'Location information unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMessage = 'Location request timed out.';
                        break;
                }
                
                foodMap.showNotification(errorMessage, 'error');
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    } else {
        foodMap.showNotification('Your browser doesn\'t support geolocation.', 'error');
    }
}

function searchNearbyLocations() {
    foodMap.searchNearbyLocations();
}

function showAllLocations() {
    foodMap.showAllLocations();
}

function addLocationFromSearch() {
    foodMap.addLocationFromSearch();
}

function clearAdminForm() {
    foodMap.clearAdminForm();
}

function deleteCurrentLocation() {
    foodMap.deleteCurrentLocation();
}

function toggleAdminMode() {
    foodMap.toggleAdminMode();
}

function closeModal() {
    foodMap.closeModal();
}

function getDirections() {
    foodMap.getDirections();
}

// Error handler for Google Maps
window.gm_authFailure = function() {
    console.error('Google Maps authentication failed');
    if (foodMap) {
        foodMap.showNotification('Google Maps failed to load. Please check the API key.', 'error');
    }
    
    // Show error message in map container
    const mapDiv = document.getElementById('map');
    if (mapDiv) {
        mapDiv.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f5f5f5;">
                <div style="text-align: center; padding: 20px;">
                    <h3 style="color: #dc3545;">⚠️ Map Loading Error</h3>
                    <p>Google Maps could not be loaded. Please check the API key configuration.</p>
                </div>
            </div>
        `;
    }
};