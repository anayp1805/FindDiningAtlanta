# atlanta_food_finder/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Admin route for Django's admin interface
    path('', include('restaurants.urls')),  # Include the restaurants app URLs
]
