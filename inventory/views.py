from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db.models import Q

class MaterialModelViewset(viewsets.ModelViewSet):
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
        request.data.pop('material_project', None)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            material=serializer.save()
            for materialOP in material_project:
                MaterialOnProject.objects.create(material=material, **materialOP)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MaterialOnProjectModelViewSet(viewsets.ModelViewSet):
    queryset = MaterialOnProject.objects.all()
    serializer_class = MaterialOnProjectSerializer
    
class ToolModelViewSet(viewsets.ModelViewSet):
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
        request.data.pop('tools_project', None)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            tool=serializer.save()
            for toolOP in tool_on_project:
                ToolOnProject.objects.create(tool=tool, **toolOP)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ToolOnProjectModelViewSet(viewsets.ModelViewSet):
    queryset = ToolOnProject.objects.all()
    serializer_class = ToolOnProjectSerializer