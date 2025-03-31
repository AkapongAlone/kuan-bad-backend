from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework import viewsets
from .models import Room,Player
from .serializers import RoomSerializer,PlayerSerializer
from .services.claude_service import ClaudeService

claude_service = ClaudeService()
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    @action(detail=True, methods=['get'])
    def ai_matchmaking(self, request, pk=None):
        room = self.get_object()
        serializer = self.get_serializer(room)
        room_data = serializer.data

        if len(room_data['players']) < 4:
            return Response(
                {"error": "Need at least 4 players for matchmaking"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            matchmaking_result = claude_service.generate_matchmaking(room_data)

            if "error" in matchmaking_result:
                return Response({
                    "room": {"id": room.id, "name": room.name},
                    "error": matchmaking_result["error"],
                    "raw_response": matchmaking_result.get("raw_response", "")
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                "room": {
                    "id": room.id,
                    "name": room.name,
                    "player_count": len(room_data['players'])
                },
                "matchmaking": {
                    "teams": matchmaking_result["teams"],
                    "match": matchmaking_result["match"],
                    "analysis": matchmaking_result["analysis"]
                }
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

