# restaurants/models.py
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    favorite_cuisine = models.CharField(max_length=255)
    favorite_dish = models.CharField(max_length=255)
    dietary_restrictions = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.username

class FavoriteRestaurant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant_name = models.CharField(max_length=255)
    restaurant_address = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} likes {self.restaurant_name}"
