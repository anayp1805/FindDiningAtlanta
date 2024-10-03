# restaurants/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import UserRegistrationForm, UserForm, UserProfileForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.http import JsonResponse
import googlemaps
import requests
from .models import UserProfile
import json
from geopy.distance import geodesic
from django.contrib.auth.decorators import login_required
from .models import FavoriteRestaurant



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('restaurant_list')  # Redirect to homepage
    else:
        form = AuthenticationForm()

    return render(request, 'restaurants/login.html', {'form': form})

def signup_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            # Automatically log the user in after signup
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(username=email, password=password)
            login(request, user)
            return redirect('restaurant_list')  # Redirect to homepage
    else:
        form = UserRegistrationForm()

    return render(request, 'restaurants/register.html', {'form': form})





def restaurant_list(request):
    closest_restaurants = []
    cuisine_types = ['Italian', 'Chinese', 'Mexican', 'American']  # Example cuisines
    user_favorites = []

    if request.user.is_authenticated:
        user_favorites = FavoriteRestaurant.objects.filter(user=request.user).values_list('restaurant_name', flat=True)

    if request.method == 'POST':
        user_lat = request.POST.get('lat')
        user_lng = request.POST.get('lng')

        # Store the user's location in the session
        request.session['user_lat'] = user_lat
        request.session['user_lng'] = user_lng

    else:
        # Check if location is already stored in the session
        user_lat = request.session.get('user_lat')
        user_lng = request.session.get('user_lng')

    # Ensure location is available before proceeding
    if not user_lat or not user_lng:
        return render(request, 'restaurants/restaurant_list.html', {'error': 'Location not provided or allowed.'})

    # Get the values from sliders or use defaults
    max_distance = request.GET.get('distance', 25)  # Default to 25km if not set
    min_rating = request.GET.get('rating', 0)  # Default to 0 rating if not set
    sort_order = request.GET.get('sort_order', 'asc')  # Ascending by default

    try:
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        # Use radius instead of rank_by for more control over distance filtering
        places_result = gmaps.places_nearby(
            location=(float(user_lat), float(user_lng)),
            radius=int(float(max_distance) * 1000),  # Convert km to meters
            type='restaurant'
        )

        for place in places_result['results']:
            restaurant_rating = place.get('rating', 0)
            if restaurant_rating >= float(min_rating):
                restaurant = {
                    'name': place.get('name'),
                    'rating': restaurant_rating,
                    'address': place.get('vicinity'),
                    'cuisine': ', '.join(place.get('types', [])),  # Join types for easy display
                    'images': [
                        f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={settings.GOOGLE_MAPS_API_KEY}"
                        for photo in place.get('photos', [])[:1]],
                    'location': place['geometry']['location']  # Add location for distance calculation
                }

                # Calculate the distance between user and restaurant
                restaurant_coords = (restaurant['location']['lat'], restaurant['location']['lng'])
                user_coords = (float(user_lat), float(user_lng))
                restaurant['distance'] = geodesic(user_coords, restaurant_coords).km  # Distance in km

                closest_restaurants.append(restaurant)

        # Sort by distance if requested
        if sort_order == 'desc':
            closest_restaurants = sorted(closest_restaurants, key=lambda x: x['distance'], reverse=True)
        else:
            closest_restaurants = sorted(closest_restaurants, key=lambda x: x['distance'])

    except Exception as e:
        return render(request, 'restaurants/restaurant_list.html', {'error': str(e)})

    return render(request, 'restaurants/restaurant_list.html', {
        'restaurants': closest_restaurants,
        'cuisine_types': cuisine_types,
        'user_favorites': user_favorites
    })



def home(request):
    favorite_restaurants = []

    if request.user.is_authenticated:
        try:
            # Fetch user's favorite cuisine from the profile
            user_profile = UserProfile.objects.get(user=request.user)
            favorite_cuisine = user_profile.favorite_cuisine

            # Get restaurants by user's favorite cuisine
            favorite_restaurants, error = get_restaurants_by_cuisine(favorite_cuisine)

            if error:
                favorite_restaurants = []  # Handle the case where there's an error

            # Limit the number of restaurants to 3
            favorite_restaurants = favorite_restaurants[:3]

        except UserProfile.DoesNotExist:
            # If the user does not have a profile or favorite cuisine set, handle the case
            favorite_cuisine = None
            favorite_restaurants = []

    return render(request, 'restaurants/home.html', {
        'favorite_restaurants': favorite_restaurants
    })


# Search for a restaurant 

# Google Places API endpoint
PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
DETAILS_API_URL = "https://maps.googleapis.com/maps/api/place/details/json"
TEXT_SEARCH_API_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

def get_restaurant_details(restaurant_name):
    if not restaurant_name:
        return None, "No restaurant name provided."

    # Step 1: Search for the restaurant using the 'find place from text' endpoint
    params = {
        'input': restaurant_name,
        'inputtype': 'textquery',
        'fields': 'place_id',
        'key': settings.GOOGLE_MAPS_API_KEY
    }

    response = requests.get(PLACES_API_URL, params=params)
    data = response.json()

    if not data.get('candidates'):
        return None, "No results found for this restaurant."

    place_id = data['candidates'][0].get('place_id')
    if not place_id:
        return None, "Failed to retrieve the place ID for the restaurant."

    # Step 3: Fetch details using the place_id
    details_params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,rating,formatted_phone_number,opening_hours,website,photos,price_level,reviews,business_status,url,types,user_ratings_total,geometry',
        'key': settings.GOOGLE_MAPS_API_KEY
    }

    details_response = requests.get(DETAILS_API_URL, params=details_params)
    details_data = details_response.json()

    if 'result' not in details_data:
        return None, "Failed to retrieve details for this restaurant."

    restaurant = details_data['result']

    # Extract multiple photo URLs (up to 5) with higher resolution
    photos = []
    if restaurant.get('photos'):
        for photo in restaurant['photos'][:5]:  # Limit to 5 photos
            photo_reference = photo['photo_reference']
            # Increase maxwidth for better image quality (max is 1600)
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1600&photoreference={photo_reference}&key={settings.GOOGLE_MAPS_API_KEY}"
            photos.append(photo_url)

    # Extract reviews (if available)
    reviews = []
    if restaurant.get('reviews'):
        for review in restaurant['reviews']:
            reviews.append({
                'author_name': review.get('author_name'),
                'rating': review.get('rating'),
                'text': review.get('text'),
                'time': review.get('relative_time_description')  # This often includes how long ago the review was posted
            })

    return restaurant, photos, reviews, None


def restaurant_details_view(request, restaurant_name):
    # Get the restaurant details using the provided method
    restaurant, photos, reviews, error = get_restaurant_details(restaurant_name)
    if error:
        return render(request, 'error.html', {'error_message': error})

    context = {
        'restaurant': restaurant,
        'photos': photos,
        'reviews': reviews,
    }
    return render(request, 'restaurants/restaurantdetails.html', context)

def get_restaurants_by_cuisine(cuisine, location="33.7490,-84.3880", radius=5000):
    """
    This function searches for restaurants that serve the given cuisine.
    :param cuisine: The type of cuisine (e.g., "Italian", "Mexican")
    :param location: Location coordinates (default: Atlanta, GA)
    :param radius: Search radius in meters (default: 5000 meters, ~3 miles)
    :return: List of restaurants or an error message.
    """
    params = {
        'query': f"{cuisine} restaurants",
        'location': location,
        'radius': radius,
        'type': 'restaurant',
        'key': settings.GOOGLE_MAPS_API_KEY
    }

    # Send a request to the Google Places Text Search API
    response = requests.get(TEXT_SEARCH_API_URL, params=params)
    data = response.json()

    if data.get('status') != "OK":
        return None, f"Error: {data.get('status')}"

    restaurants = data.get('results', [])

    # Add photo URLs to the restaurant data
    for restaurant in restaurants:
        if 'photos' in restaurant:
            # Extract photo reference and construct the photo URL
            photo_reference = restaurant['photos'][0]['photo_reference']
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={settings.GOOGLE_MAPS_API_KEY}"
            restaurant['photo_url'] = photo_url
        else:
            # If no photo is available, set a default image URL
            restaurant['photo_url'] = '/static/img/default_restaurant.jpg'

    # Limit the results to 10 restaurants
    return restaurants[:10], None


def search_restaurant(request):
    if request.method == "POST":
        # Check if we're searching by restaurant name
        restaurant_name = request.POST.get('restaurant_name')
        if restaurant_name:
            # Search by restaurant name
            restaurant_details, photos, error = get_restaurant_details(restaurant_name)

            if error:
                return render(request, 'restaurants/restaurant.html', {'error': error})

            context = {
                'restaurant': restaurant_details,
                'photos': photos
            }
            return render(request, 'restaurants/restaurant.html', context)

        # Check if we're searching by cuisine
        cuisine_type = request.POST.get('cuisine_type')
        near_me = request.POST.get('near_me')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        # If "Near Me" is checked, use current location
        if near_me and latitude and longitude:
            location = f"{latitude},{longitude}"
            restaurants, error = get_restaurants_by_cuisine(cuisine_type, location=location)

            if error:
                return render(request, 'restaurants/restaurant.html', {'error': error})

            context = {
                'cuisine_restaurants': restaurants,
                'cuisine_type': cuisine_type
            }
            return render(request, 'restaurants/restaurant.html', context)

        # Otherwise, search by cuisine without location
        elif cuisine_type:
            restaurants, error = get_restaurants_by_cuisine(cuisine_type)

            if error:
                return render(request, 'restaurants/restaurant.html', {'error': error})

            context = {
                'cuisine_restaurants': restaurants,
                'cuisine_type': cuisine_type
            }
            return render(request, 'restaurants/restaurant.html', context)

    return render(request, 'restaurants/restaurant.html')

def map(request):
    # Default location (e.g., Atlanta)
    default_location = {
        'lat': 33.7490,
        'lng': -84.3880,
    }
    # Pass Google Maps API key and default location to the template
    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'default_location': default_location,
    }
    return render(request, 'restaurants/map.html', context)

def profile_view(request):
    user = request.user
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        user_profile = None

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('profile')  # Redirect to the profile page after saving

    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user_profile)

    return render(request, 'restaurants/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def map_view(request):
    # Default to some location, for example, Atlanta
    default_location = {
        'lat': 33.7490,
        'lng': -84.3880,
    }

    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'default_location': default_location,
    }

    return render(request, 'restaurants/map.html', context)

def search_restaurants(request):
    if request.method == 'POST':
        # Parse the request body to get search parameters
        data = json.loads(request.body)
        restaurant_name = data.get('restaurant_name', '')
        cuisine_type = data.get('cuisine_type', '')

        # Get user's location from session or use a default location (Atlanta)
        user_lat = request.session.get('user_lat', '33.7490')
        user_lng = request.session.get('user_lng', '-84.3880')

        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

        # Build the query string based on user input
        query = f"{cuisine_type} {restaurant_name} restaurants" if cuisine_type or restaurant_name else 'restaurants'

        # Search for nearby places using Google Places API
        try:
            places_result = gmaps.places_nearby(
                location=(user_lat, user_lng),
                radius=5000,  # 5 km radius
                keyword=query,
                type='restaurant'
            )
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        # Extract the relevant restaurant data
        restaurants = []
        for place in places_result['results']:
            restaurants.append({
                'name': place['name'],
                'lat': place['geometry']['location']['lat'],
                'lng': place['geometry']['location']['lng'],
                'address': place.get('vicinity', 'No address available'),
                'rating': place.get('rating', 'No rating available')
            })

        # Return the list of restaurants as JSON
        return JsonResponse({'restaurants': restaurants})

    # If not a POST request, return an error response
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def like_restaurant(request, restaurant_name, restaurant_address):
    # Check if the restaurant is already in the favorites list
    favorite = FavoriteRestaurant.objects.filter(user=request.user, restaurant_name=restaurant_name).first()

    if favorite:
        # If it already exists, unlike (remove from favorites)
        favorite.delete()
    else:
        # If it doesn't exist, add to favorites
        FavoriteRestaurant.objects.create(user=request.user, restaurant_name=restaurant_name)
    return redirect('restaurant_list')


@login_required
def favorites_list(request):
    favorites = FavoriteRestaurant.objects.filter(user=request.user)

    # Prepare a list to hold restaurant details
    restaurant_details_list = []

    for favorite in favorites:
        restaurant, photos, reviews, error = get_restaurant_details(favorite.restaurant_name)
        if restaurant and not error:
            # Append the restaurant details along with the photos
            restaurant_details_list.append({
                'name': restaurant.get('name'),
                'address': restaurant.get('formatted_address'),
                'rating': restaurant.get('rating'),
                'image': photos[0] if photos else None,  # Take the first photo if available
                'url': restaurant.get('url')
            })

    return render(request, 'restaurants/favorites.html', {'restaurant_details_list': restaurant_details_list})


def get_cuisine(request, restaurant_name):
    API_KEY = settings.YELP_API_KEY;  # Your Yelp API key
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }
    latitude = 33.7490  # Example latitude (Atlanta)
    longitude = -84.3880  # Example longitude (Atlanta)
    params = {
        'term': restaurant_name,
        'latitude': latitude,
        'longitude': longitude,
        'limit': 1  # Get only one result for simplicity
    }
    response = requests.get('https://api.yelp.com/v3/businesses/search', headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'businesses' in data and len(data['businesses']) > 0:
            business = data['businesses'][0]
            if business['categories']:
                first_cuisine = business['categories'][0]['title']
                return JsonResponse({'cuisine': first_cuisine})

    return JsonResponse({'cuisine': 'Not available'}, status=404)

def about(request):
    return render(request, "restaurants/about.html")

