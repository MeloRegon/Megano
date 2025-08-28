from django.db import models
from django.contrib.auth.models import User


class Avatar(models.Model):
    src = models.ImageField("Картинка",upload_to='app_users/avatars/user_avatars/')
    alt = models.CharField("Описание", max_length=128, blank=True, default='')

    class Meta:
        verbose_name = 'Аватар'
        verbose_name_plural = "Аватар"

    def __str__(self):
        return self.alt or f'Avatar #{self.pk}'


class Profile(models.Model):
    user = models.OneToOneField( User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField("Полное Имя",max_length=128)
    email = models.EmailField("Почта",unique=True, null=True, blank=True)
    phone = models.CharField("Телефон",max_length=32, unique=True, null=True, blank=True)
    balance = models.DecimalField("Баланс",max_digits=10, decimal_places=2, default=0)
    avatar = models.ForeignKey(Avatar, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профиль'

    def __str__(self):
        return self.full_name