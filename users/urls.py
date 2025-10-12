from django.urls import path
from .views import (
    SignInView,
    SignUpView,
    SignOutView,
    ProfileApi,
    )


urlpatterns = [
    path('sign-in', SignInView.as_view(), name='post_sign_in'),
    path('sign-in/', SignInView.as_view()),
    path('sign-up', SignUpView.as_view(), name='post_sign_up'),
    path('sign-out', SignOutView.as_view(), name='post_sign_out'),
    path('profile', ProfileApi.as_view(), name='profile'),
]