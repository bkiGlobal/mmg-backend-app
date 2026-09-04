from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError as DjangoValidationError
from core.permissions import (
    INVENTORY_WRITE_ROLES,
    ProjectScopedQuerysetMixin,
    RoleBasedPermission,
)
from .services import complete_tool_maintenance, receive_purchase_request


def normalize_foreign_keys(payload, field_names):
    if hasattr(payload, 'getlist'):
        normalized = {key: payload.get(key) for key in payload.keys()}
    else:
        normalized = dict(payload)
    for field_name in field_names:
        id_field = f'{field_name}_id'
        if field_name in normalized and id_field not in normalized:
            normalized[id_field] = normalized.pop(field_name)
    return normalized


class InventoryViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleBasedPermission]
    write_roles = INVENTORY_WRITE_ROLES


class InventoryProjectViewSet(
    ProjectScopedQuerysetMixin, InventoryViewSet
):
    global_project_roles = {'logistic'}


class MaterialModelViewset(InventoryViewSet):
    queryset = Material.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('category', 'brand', 'unit') \
                           .prefetch_related('material_project', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            category = self.request.query_params.get('category', None)
            brand = self.request.query_params.get('brand', None)
            unit = self.request.query_params.get('unit', None)
            standart_price = self.request.query_params.get('standart_price', None)
            query = Q()
            if search_query:
                query &= Q(name__icontains=search_query) | Q(code__icontains=search_query) | Q(descriptions__icontains=search_query)
            if category:
                query &= Q(category__id=category)
            if brand:
                query &= Q(brand__id=brand)
            if unit:
                query &= Q(unit__id=unit)
            if standart_price:
                query &= Q(standart_price__lte=standart_price)
            queryset = queryset.filter(query).distinct()
        return queryset
        
    def get_serializer_class(self):
        if self.action == 'list':
            return MaterialSimpleSerializer
        return MaterialSerializer

    def create(self, request, *args, **kwargs):
        material_project = request.data.get('material_project', [])
        data = request.data.copy()
        data.pop('material_project', None)
        data = normalize_foreign_keys(
            data, ('category', 'brand', 'unit')
        )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            material = serializer.save()
            for materialOP in material_project:
                child_data = normalize_foreign_keys(
                    materialOP,
                    ('project', 'approved_by'),
                )
                child_data['material_id'] = material.pk
                child_serializer = MaterialOnProjectSerializer(
                    data=child_data,
                    context={'request': request},
                )
                child_serializer.is_valid(raise_exception=True)
                child_serializer.save()

        return Response(
            self.get_serializer(material).data,
            status=status.HTTP_201_CREATED,
        )

class MaterialOnProjectModelViewSet(InventoryProjectViewSet):
    queryset = MaterialOnProject.objects.all()
    serializer_class = MaterialOnProjectSerializer
    
class ToolModelViewSet(InventoryViewSet):
    queryset = Tool.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('category', ) \
                           .prefetch_related('tools_project', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            category = self.request.query_params.get('category', None)
            amount = self.request.query_params.get('amount', None)
            available = self.request.query_params.get('available', None)
            query = Q()
            if search_query:
                query &= Q(name__icontains=search_query) | Q(serial_number__icontains=search_query) | Q(conditions__icontains=search_query)
            if category:
                query &= Q(category__id=category)
            if amount:
                query &= Q(amount__lte=amount)
            if available:
                query &= Q(available__lte=available)
            queryset = queryset.filter(query).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ToolSimpleSerializer
        return ToolSerializer

    def create(self, request, *args, **kwargs):
        tool_on_project = request.data.get('tools_project', [])
        data = request.data.copy()
        data.pop('tools_project', None)
        data = normalize_foreign_keys(data, ('category',))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            tool = serializer.save()
            for toolOP in tool_on_project:
                child_data = normalize_foreign_keys(
                    toolOP, ('project',)
                )
                child_data['tool_id'] = tool.pk
                child_serializer = ToolOnProjectSerializer(
                    data=child_data,
                    context={'request': request},
                )
                child_serializer.is_valid(raise_exception=True)
                child_serializer.save()

        return Response(
            self.get_serializer(tool).data,
            status=status.HTTP_201_CREATED,
        )

class ToolOnProjectModelViewSet(InventoryProjectViewSet):
    queryset = ToolOnProject.objects.all()
    serializer_class = ToolOnProjectSerializer


class StockMovementModelViewSet(
    ProjectScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet
):
    permission_classes = [RoleBasedPermission]
    global_project_roles = {'logistic'}
    queryset = StockMovement.objects.select_related(
        'project', 'material', 'material__category', 'material__unit'
    )
    serializer_class = StockMovementSerializer


class PurchaseRequestModelViewSet(InventoryProjectViewSet):
    queryset = PurchaseRequest.objects.select_related(
        'project', 'material', 'requested_by', 'approved_by'
    )
    serializer_class = PurchaseRequestSerializer

    def perform_create(self, serializer):
        serializer.save(
            requested_by=getattr(self.request.user, 'profile', None)
        )

    def receive(self, request, pk=None):
        try:
            purchase = receive_purchase_request(
                self.get_object(), request.user
            )
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, 'message_dict')
                else exc.messages
            )
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(purchase).data)


class ToolMaintenanceModelViewSet(InventoryViewSet):
    queryset = ToolMaintenance.objects.select_related('tool', 'tool__category')
    serializer_class = ToolMaintenanceSerializer

    def complete(self, request, pk=None):
        try:
            maintenance = complete_tool_maintenance(
                self.get_object(), request.user
            )
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, 'message_dict')
                else exc.messages
            )
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(maintenance).data)
