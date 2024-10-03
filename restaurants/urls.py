from django.urls import path
from django.contrib.auth import logout
from django.shortcuts import redirect
from . import views
from django.contrib.auth import views as auth_views


def custom_logout_view(request):
    logout(request)  # Logs out the user
    return redirect('home')  # Redirect to the home page


urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.signup_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('restaurant/', views.search_restaurant, name='restaurant-search'),
    path('logout/', custom_logout_view, name='logout'),
    path('restaurant/<str:restaurant_name>/', views.restaurant_details_view, name='restaurant_details'),
    path('profile/', views.profile_view, name='profile'),
    path('search_restaurants/', views.search_restaurants, name='search_restaurants'),
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('like/<path:restaurant_name>/<path:restaurant_address>/', views.like_restaurant, name='like_restaurant'),  # Ensure this is defined
    path('get-cuisine/<str:restaurant_name>/', views.get_cuisine, name='get_cuisine'),
    path('about/', views.about, name='about'),



    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(success_url='/login'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('map/', views.map, name='map'),
]
