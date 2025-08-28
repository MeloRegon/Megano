from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Profile


print('SIGNALS MODULE IMPORTED')

@receiver(post_save, sender=User)
def create_profile_on_user_created(sender, instance, created, **kwargs):
    print('USER post_save signal receved, created=', created)
    if created:
        Profile.objects.get_or_create(user=instance)