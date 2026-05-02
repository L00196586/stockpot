from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

DIETARY_CHOICES = [
    ("vegetarian", "Vegetarian"),
    ("vegan", "Vegan"),
    ("gluten_free", "Gluten Free"),
    ("dairy_free", "Dairy Free"),
    ("nut_free", "Nut Free"),
    ("halal", "Halal"),
    ("kosher", "Kosher"),
    ("keto", "Keto"),
]

VALID_DIETARY_KEYS = {key for key, _ in DIETARY_CHOICES}


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    dietary_preferences = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Profile({self.user.email})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
