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
    path('stock-movement/', StockMovementModelViewSet.as_view({
        'get': 'list',
    }), name='stock_movement_list'),
    path('stock-movement/<str:pk>/', StockMovementModelViewSet.as_view({
        'get': 'retrieve',
    }), name='stock_movement_detail'),
    path('purchase-request/', PurchaseRequestModelViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='purchase_request_list'),
    path('purchase-request/<str:pk>/', PurchaseRequestModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='purchase_request_detail'),
    path(
        'purchase-request/<str:pk>/receive/',
        PurchaseRequestModelViewSet.as_view({'post': 'receive'}),
        name='purchase_request_receive',
    ),
    path('tool-maintenance/', ToolMaintenanceModelViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='tool_maintenance_list'),
    path('tool-maintenance/<str:pk>/', ToolMaintenanceModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='tool_maintenance_detail'),
    path(
        'tool-maintenance/<str:pk>/complete/',
        ToolMaintenanceModelViewSet.as_view({'post': 'complete'}),
        name='tool_maintenance_complete',
    ),
]
