from rest_framework import serializers
from .models import Room,Player


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id','room', 'name', 'skill', 'join_time', 'number_of_matches', 'number_of_shuttlecock']


class RoomSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = '__all__'
