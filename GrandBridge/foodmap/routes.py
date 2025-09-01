from flask import render_template, Blueprint, request, jsonify
from GrandBridge.models import db, Location
from flask_login import current_user, login_required
import math

foodmap = Blueprint('foodmap', __name__)

@foodmap.route('/foodmap')
@login_required
def view_map():
    """Main map view with location count"""
    location_count = Location.query.count()
    return render_template('map.html', 
                         is_admin=current_user.is_admin,
                         location_count=location_count)
@foodmap.route('/foodmap/save_location', methods=['POST'])
@login_required
def save_location():
    """Admin: Save a new food pickup location"""
    if not current_user.is_admin:
        return jsonify({'status': 'failed', 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        lat = data.get('lat')
        lng = data.get('lng')
        name = data.get('name', 'Food Pickup Point')
        address = data.get('address', '')
        
        if lat is None or lng is None:
            return jsonify({'status': 'failed', 'message': 'Invalid coordinates'}), 400
        
        # Check for duplicate locations (within 50 meters)
        existing = Location.query.all()
        for loc in existing:
            distance = calculate_distance(lat, lng, loc.latitude, loc.longitude)
            if distance < 0.05:  # 50 meters
                return jsonify({
                    'status': 'failed', 
                    'message': 'A location already exists very close to this point'
                }), 400
        
        location = Location(
            latitude=float(lat),
            longitude=float(lng),
            name=name,
            address=address
        )
        db.session.add(location)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'location': {
                'id': location.id,
                'lat': location.latitude,
                'lng': location.longitude,
                'name': location.name,
                'address': location.address
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'failed', 'message': str(e)}), 500

@foodmap.route('/foodmap/get_locations', methods=['GET'])
@login_required
def get_locations():
    """Get all food pickup locations"""
    try:
        locations = Location.query.all()
        data = [{
            'id': loc.id,
            'lat': loc.latitude,
            'lng': loc.longitude,
            'name': loc.name or 'Food Pickup Point',
            'address': loc.address or 'Address not specified'
        } for loc in locations]
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@foodmap.route('/foodmap/get_nearby_locations', methods=['POST'])
@login_required
def get_nearby_locations():
    """Get locations within a specified radius of user's position"""
    try:
        data = request.get_json()
        user_lat = float(data.get('lat'))
        user_lng = float(data.get('lng'))
        radius = float(data.get('radius', 5))  # Default 5km radius
        
        locations = Location.query.all()
        nearby_locations = []
        
        for loc in locations:
            distance = calculate_distance(user_lat, user_lng, 
                                        loc.latitude, loc.longitude)
            if distance <= radius:
                nearby_locations.append({
                    'id': loc.id,
                    'lat': loc.latitude,
                    'lng': loc.longitude,
                    'name': loc.name or 'Food Pickup Point',
                    'address': loc.address or 'Address not specified',
                    'distance': round(distance, 2)
                })
        
        # Sort by distance
        nearby_locations.sort(key=lambda x: x['distance'])
        
        return jsonify({
            'status': 'success',
            'locations': nearby_locations,
            'total': len(nearby_locations)
        })
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 500

@foodmap.route('/foodmap/delete_location/<int:location_id>', methods=['DELETE'])
@login_required
def delete_location(location_id):
    """Admin: Delete a food pickup location"""
    if not current_user.is_admin:
        return jsonify({'status': 'failed', 'message': 'Unauthorized'}), 403
    
    try:
        location = Location.query.get(location_id)
        if not location:
            return jsonify({'status': 'failed', 'message': 'Location not found'}), 404
        
        db.session.delete(location)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Location deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'failed', 'message': str(e)}), 500
    

@foodmap.route('/foodmap/bulk_upload', methods=['POST'])
@login_required
def bulk_upload_locations():
    """Admin: Upload multiple locations at once"""
    if not current_user.is_admin:
        return jsonify({'status': 'failed', 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        locations_data = data.get('locations', [])
        
        if not locations_data:
            return jsonify({'status': 'failed', 'message': 'No locations provided'}), 400
        
        added_count = 0
        skipped_count = 0
        errors = []
        
        for loc_data in locations_data:
            try:
                lat = float(loc_data.get('lat'))
                lng = float(loc_data.get('lng'))
                name = loc_data.get('name', 'Food Pickup Point')
                address = loc_data.get('address', '')
                
                # Check for duplicates
                duplicate = False
                existing = Location.query.all()
                for existing_loc in existing:
                    distance = calculate_distance(lat, lng, 
                                                existing_loc.latitude, 
                                                existing_loc.longitude)
                    if distance < 0.05:  # 50 meters
                        duplicate = True
                        break
                
                if duplicate:
                    skipped_count += 1
                    continue
                
                location = Location(
                    latitude=lat,
                    longitude=lng,
                    name=name,
                    address=address
                )
                db.session.add(location)
                added_count += 1
                
            except Exception as e:
                errors.append(f"Error processing location: {str(e)}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'added': added_count,
            'skipped': skipped_count,
            'errors': errors
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'failed', 'message': str(e)}), 500

@foodmap.route('/foodmap/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Get statistics about food pickup locations"""
    try:
        total_locations = Location.query.count()
        
        # Get locations by area (you could group by city/district if you have that data)
        locations = Location.query.all()
        
        # Basic stats
        stats = {
            'total_locations': total_locations,
            'active_locations': total_locations,  # Could add active/inactive status later
            'locations_added_today': 0,  # Would need created_at timestamp
            'most_recent_location': None
        }
        
        if locations:
            # Get most recent (by ID as proxy if no timestamp)
            most_recent = max(locations, key=lambda x: x.id)
            stats['most_recent_location'] = {
                'name': most_recent.name,
                'address': most_recent.address
            }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Utility function
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points on Earth using Haversine formula
    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@foodmap.route('/foodmap/search_locations', methods=['POST'])
@login_required
def search_locations():
    """Search locations by keyword and/or proximity"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        user_lat = data.get('lat')
        user_lng = data.get('lng')
        radius = data.get('radius')
        
        # Start with all active locations
        query = Location.query
        
        # Apply keyword filter if provided
        if keyword:
            # Case-insensitive search in name field
            search_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    Location.name.ilike(search_pattern),
                    Location.address.ilike(search_pattern),
                    Location.food_types.ilike(search_pattern)
                )
            )
        
        locations = query.all()
        
        # Calculate distances if user location provided
        results = []
        for loc in locations:
            location_dict = {
                'id': loc.id,
                'lat': loc.latitude,
                'lng': loc.longitude,
                'name': loc.name or 'Food Pickup Point',
                'address': loc.address or 'Address not specified',
                'food_types': loc.food_types,
                'operating_hours': loc.operating_hours
            }
            
            # Calculate distance if user coordinates provided
            if user_lat is not None and user_lng is not None:
                distance = calculate_distance(
                    float(user_lat), float(user_lng),
                    loc.latitude, loc.longitude
                )
                location_dict['distance'] = round(distance, 2)
                
                # Filter by radius if specified
                if radius is not None and distance > float(radius):
                    continue
            
            results.append(location_dict)
        
        # Sort by distance if distances were calculated
        if user_lat is not None and user_lng is not None:
            results.sort(key=lambda x: x.get('distance', float('inf')))
        
        return jsonify({
            'status': 'success',
            'locations': results,
            'total': len(results),
            'keyword': keyword
        })
        
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 500


@foodmap.route('/foodmap/autocomplete', methods=['GET'])
@login_required
def autocomplete_locations():
    """Provide location name suggestions for autocomplete"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        # Find locations with names starting with or containing the query
        locations = Location.query.filter(
            Location.name.ilike(f'%{query}%')
        ).limit(10).all()
        
        # Return unique location names
        suggestions = []
        seen = set()
        for loc in locations:
            if loc.name and loc.name not in seen:
                suggestions.append({
                    'id': loc.id,
                    'name': loc.name,
                    'address': loc.address
                })
                seen.add(loc.name)
        
        return jsonify(suggestions)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500