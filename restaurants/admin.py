from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, FavoriteRestaurant

# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

# Define an inline admin descriptor for FavoriteRestaurant model
class FavoriteRestaurantInline(admin.TabularInline):
    model = FavoriteRestaurant
    can_delete = True
    extra = 0  # Number of extra blank fields for new entries
    verbose_name_plural = 'Favorite Restaurants'
    fk_name = 'user'

# Extend the existing UserAdmin to include UserProfile and FavoriteRestaurant inlines
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, FavoriteRestaurantInline)

    # Customize list display to show extra fields in the user list in the admin panel
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_favorite_cuisine')
    list_select_related = ('userprofile',)

    def get_favorite_cuisine(self, instance):
        return instance.userprofile.favorite_cuisine
    get_favorite_cuisine.short_description = 'Favorite Cuisine'

# Unregister the default User admin and register the customized one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

