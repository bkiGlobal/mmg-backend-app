from django.urls import path
from .views import *

urlpatterns = [
    path('material/', MaterialModelViewset.as_view({
        'get': 'list',
        'post': 'create'
    }), name='material_list'),
    path('material/<str:pk>/', MaterialModelViewset.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='material_detail'),
    path('material-on-project/', MaterialOnProjectModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='material_on_project_list'),
    path('material-on-project/<str:pk>/', MaterialOnProjectModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='material_on_project_detail'),
    path('tool/', ToolModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='tool_list'),
    path('tool/<str:pk>/', ToolModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='tool_detail'),
    path('tool-on-project/', ToolOnProjectModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='tool_on_project_list'),
    path('tool-on-project/<str:pk>/', ToolOnProjectModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='tool_on_project_detail'),
]