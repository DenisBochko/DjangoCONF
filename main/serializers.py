from django.contrib.auth.models import User
from rest_framework import serializers
from .models import *


class UserSerializer(serializers.ModelSerializer):
    # Добавляем поля из связанной модели UserProfile
    is_admin = serializers.BooleanField(source='profile.is_admin', required=False)
    photo = serializers.ImageField(source='profile.photo', required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_admin', 'photo']
        extra_kwargs = {
            'password': {'write_only': True},  # Пароль только для записи
            'is_admin': {'read_only': True},   # Поле is_admin только для чтения
        }

    def create(self, validated_data):
        # Извлекаем данные профиля из validated_data
        profile_data = validated_data.pop('profile', {})
        # Создаем пользователя
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        # Создаем профиль пользователя
        UserProfile.objects.create(user=user, **profile_data)
        return user

    def update(self, instance, validated_data):
        # Извлекаем данные профиля из validated_data
        profile_data = validated_data.pop('profile', {})
        # Обновляем основные поля пользователя
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        # Обновляем профиль пользователя
        profile = instance.profile
        profile.is_admin = profile_data.get('is_admin', profile.is_admin)
        if 'photo' in profile_data:
            profile.photo = profile_data['photo']
        profile.save()

        return instance


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'registration_link', 'date', 'admin']

class AgendaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgendaItem
        fields = ['id', 'meeting', 'title', 'description', 'materials', 'meeting_type', 'summary_datetime']

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'agenda_item', 'user', 'vote', 'timestamp', 'signed_vote']
        read_only_fields = ['user', 'timestamp']

    def create(self, validated_data):
        # Привязываем голос к пользователю, переданному в save()
        user = validated_data.pop('user', None)
        if not user:
            raise serializers.ValidationError("User is required")
        return Vote.objects.create(user=user, **validated_data)