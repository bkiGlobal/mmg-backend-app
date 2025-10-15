from django.urls import path
from .views import *

urlpatterns = [
    path('material/', MaterialAPIView.as_view(), name='material_list'),
    path('material/<str:pk>/', MaterialAPIView.as_view(), name='material_detail'),
    path('material-on-project/', MaterialOnProjectAPIView.as_view(), name='material_on_project_list'),
    path('material-on-project/<str:pk>/', MaterialOnProjectAPIView.as_view(), name='material_on_project_detail'),
    path('tool/', ToolAPIView.as_view(), name='tool_list'),
    path('tool/<str:pk>/', ToolAPIView.as_view(), name='tool_detail'),
    path('tool-on-project/', ToolOnProjectAPIView.as_view(), name='tool_on_project_list'),
    path('tool-on-project/<str:pk>/', ToolOnProjectAPIView.as_view(), name='tool_on_project_detail'),
]