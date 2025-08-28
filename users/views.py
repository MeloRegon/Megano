from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie

from users.serializers import ProfileSerializer
from .models import Profile

class SignInView(APIView):

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate( request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({'message': 'Login successful'},status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid credentials'},status=status.HTTP_401_UNAUTHORIZED)


class SignUpView(APIView):

    def post(self,request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        name = (request.data.get('name') or '').strip()
        email = (request.data.get('email') or '').strip().lower()

        if not username or not password or not name:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if Profile.objects.filter(email=email).exists():
            return Response({'error': 'Email already in use'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.create_user(username=username, password=password)
        except IntegrityError:
            return Response({'error': 'Username already in use'}, status=status.HTTP_409_CONFLICT)
        user.profile.full_name = name
        user.profile.email = email
        user.profile.save()

        auth_user = authenticate(request, username=username, password=password)
        if auth_user is not None:
            login(request, auth_user)
            return Response({'message': 'Created'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Invalid'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SignOutView(APIView):

    def post(self, request):
        logout(request)
        return Response( {'message': 'Logged out'}, status=status.HTTP_200_OK)


class ProfileApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        response = ProfileSerializer(profile).data
        return Response(response)

    def post(self, request):
        profile = request.user.profile
        data = request.data.copy()

        if 'phone' in data:
            value = (data['phone'] or '').strip()
            if value == '':
                data['phone'] = None
            else:
                data['phone'] = value

        serializer = ProfileSerializer(profile, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'detail': 'ok'})