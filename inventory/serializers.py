from rest_framework import serializers
from .models import *
from core.serializers import *
from project.serializers import ProjectSimpleSerializer
from team.serializers import ProfileSimpleSerializer

class MaterialOnProjectSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    approved_by = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = MaterialOnProject
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class MaterialSerializer(serializers.ModelSerializer):
    category = MaterialCategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    unit = UnitTypeSerializer(read_only=True)
    material_project = MaterialOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ToolOnProjectSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = ToolOnProject
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ToolSerializer(serializers.ModelSerializer):
    category = ToolCategorySerializer(read_only=True)
    tools_project = ToolOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Tool
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')