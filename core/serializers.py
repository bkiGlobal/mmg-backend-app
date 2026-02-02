from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import *
from team.models import Profile
from django.shortcuts import get_object_or_404

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        profile = get_object_or_404(Profile, user=user)
        token['id'] = str(profile.pk)

        return token
    
class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'

class IncomeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeCategory
        fields = '__all__'

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = '__all__'

class WorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkType
        fields = '__all__'

class MaterialCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialCategory
        fields = '__all__'

class ToolCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolCategory
        fields = '__all__'

class UnitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitType
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class FinanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceType
        fields = '__all__'

class PaymentViaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentVia
        fields = '__all__'