from rest_framework import serializers
from .models import Profile, Avatar

class AvatarSerializer(serializers.ModelSerializer):
    src = serializers.SerializerMethodField()

    class Meta:
        model = Avatar
        fields = ['src', 'alt']

    def get_src(self, obj):
        return obj.src.url if obj.src else ''


class ProfileSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name', required=False)
    avatar = AvatarSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ['fullName', 'email', 'phone', 'avatar']