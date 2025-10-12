
import json
from urllib.parse import parse_qs
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie

from users.serializers import ProfileSerializer
from .models import Profile


def _pull_creds(request, keys=('username','password')):
    """
    Достаёт данные и из query (?a=1), и из form/JSON (request.data),
    а также из кейса, когда фронт шлёт одну JSON-строку в единственном поле.
    """
    data = {}
    # 1) обычные query-параметры
    for k in keys:
        if k in request.query_params:
            data[k] = request.query_params.get(k)

    # 2) form-данные/JSON
    if hasattr(request, 'data') and request.data:
        if isinstance(request.data, dict):
            for k in keys:
                if k in request.data and data.get(k) in (None, ''):
                    data[k] = request.data.get(k)
        else:
            # бывает «{"username":"...", "password":"..."}» одной строкой
            try:
                blob = json.loads(str(request.data))
                for k in keys:
                    if k in blob and data.get(k) in (None, ''):
                        data[k] = blob.get(k)
            except Exception:
                pass
    return data


class SignInView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            only_key = next(iter(request.POST.keys()))
            payload = json.loads(only_key)
            username = payload.get('username')
            password = payload.get('password')
        except Exception:
            return Response('invalid request format', status=400)

        if not username or not password:
            return Response({'detail': 'username and password are required'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'detail': 'invalid credentials'}, status=401)

        login(request, user)
        return Response({'ok': True, 'username': user.get_username()}, status=200)



class SignUpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 1) пытаемся получить из DRF
        only_key = next(iter(request.POST.keys()))
        payload = json.loads(only_key)
        name = payload.get('name')
        username = payload.get('username')
        password = payload.get('password')

        if not (username and password and name):
            return Response({'detail': 'username, password and name are required'}, status=500)

        # дальше — как у вас было:
        try:
            user = User.objects.create_user(username=username, password=password)
        except IntegrityError:
            return Response({'detail': 'username already exists'}, status=500)

        # профиль/имя:
        try:
            Profile.objects.create(user=user, name=name)
        except Exception:
            user.first_name = name
            user.save(update_fields=['first_name'])

        login(request, user)
        return Response({'ok': True, 'username': user.username}, status=200)


class SignOutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logout(request)
        resp = Response({'ok': True}, status=status.HTTP_200_OK)
        resp.delete_cookie('sessionid', path='/')
        resp.delete_cookie('csrftoken', path='/')
        return resp


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