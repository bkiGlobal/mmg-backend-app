from rest_framework import status
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q

class MaterialAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            material = get_object_or_404(Material, pk=pk)
            serializer = MaterialSerializer(material)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            materials = Material.objects.all()
            search_query = request.query_params.get('search_query', None)
            category = request.query_params.get('category', None)
            brand = request.query_params.get('brand', None)
            unit = request.query_params.get('unit', None)
            standart_price = request.query_params.get('standart_price', None)
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
            materials = materials.filter(query).distinct()
            serializer = MaterialSerializer(materials, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        material_project = request.data.get('material_project', [])
        request.data.pop('material_project', None)
        serializer = MaterialSerializer(data=request.data)
        if serializer.is_valid():
            material=serializer.save()
            for materialOP in material_project:
                MaterialOnProject.objects.create(material=material, **materialOP)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        serializer = MaterialSerializer(material, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        material.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class MaterialOnProjectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            material_on_project = get_object_or_404(MaterialOnProject, pk=pk)
            serializer = MaterialOnProjectSerializer(material_on_project)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            materials_on_project = MaterialOnProject.objects.all()
            serializer = MaterialOnProjectSerializer(materials_on_project, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MaterialOnProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        material_on_project = get_object_or_404(MaterialOnProject, pk=pk)
        serializer = MaterialOnProjectSerializer(material_on_project, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        material_on_project = get_object_or_404(MaterialOnProject, pk=pk)
        material_on_project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ToolAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            tool = get_object_or_404(Tool, pk=pk)
            serializer = ToolSerializer(tool)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            tools = Tool.objects.all()
            search_query = request.query_params.get('search_query', None)
            category = request.query_params.get('category', None)
            amount = request.query_params.get('amount', None)
            available = request.query_params.get('available', None)
            query = Q()
            if search_query:
                query &= Q(name__icontains=search_query) | Q(serial_number__icontains=search_query) | Q(conditions__icontains=search_query)
            if category:
                query &= Q(category__id=category)
            if amount:
                query &= Q(amount__lte=amount)
            if available:
                query &= Q(available__lte=available)
            tools = tools.filter(query).distinct()
            serializer = ToolSerializer(tools, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        tool_on_project = request.data.get('tools_project', [])
        request.data.pop('tools_project', None)
        serializer = ToolSerializer(data=request.data)
        if serializer.is_valid():
            tool=serializer.save()
            for toolOP in tool_on_project:
                ToolOnProject.objects.create(tool=tool, **toolOP)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        tool = get_object_or_404(Tool, pk=pk)
        serializer = ToolSerializer(tool, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        tool = get_object_or_404(Tool, pk=pk)
        tool.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ToolOnProjectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            tool_on_project = get_object_or_404(ToolOnProject, pk=pk)
            serializer = ToolOnProjectSerializer(tool_on_project)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            tools_on_project = ToolOnProject.objects.all()
            serializer = ToolOnProjectSerializer(tools_on_project, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ToolOnProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        tool_on_project = get_object_or_404(ToolOnProject, pk=pk)
        serializer = ToolOnProjectSerializer(tool_on_project, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        tool_on_project = get_object_or_404(ToolOnProject, pk=pk)
        tool_on_project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)