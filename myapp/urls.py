from rest_framework.routers import DefaultRouter
from .views import PlayerViewSet,RoomViewSet

router = DefaultRouter()
router.register(r'players', PlayerViewSet)
router.register(r'rooms', RoomViewSet)

urlpatterns = router.urls

# ถ้าต้องการเพิ่ม URL แบบปกติที่ไม่ใช่ API endpoints:
# from .views import some_view_function
# urlpatterns += [
#     path('special-url/', some_view_function, name='special-url'),
# ]