from django.urls import path
from .views import (
    SignInView,
    SignUpView,
    SignOutView,
    ProfileApi,
    )


urlpatterns = [
    path('sign-in/', SignInView.as_view(), name='sign-in'),
    path('sign-up/', SignUpView.as_view(), name='sign-up'),
    path('sign-out/', SignOutView.as_view(), name='sign-out'),
    path('profile/', ProfileApi.as_view(), name='profile'),
]