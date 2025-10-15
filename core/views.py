from rest_framework import status
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q

class LocationAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            location = get_object_or_404(Location, pk=pk, is_deleted=False)
            serializer = LocationSerializer(location)
            return Response(serializer.data)
        else:
            locations = Location.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                locations = locations.filter(
                    Q(name__icontains=search_query) |
                    Q(latitude__icontains=search_query) |
                    Q(longitude__icontains=search_query)
                )
            serializer = LocationSerializer(locations, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        location = get_object_or_404(Location, pk=pk, is_deleted=False)
        serializer = LocationSerializer(location, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        location = get_object_or_404(Location, pk=pk, is_deleted=False)
        location.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ExpenseCategoryAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(ExpenseCategory, pk=pk, is_deleted=False)
            serializer = ExpenseCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = ExpenseCategory.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = ExpenseCategorySerializer(categories, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        category = get_object_or_404(ExpenseCategory, pk=pk, is_deleted=False)
        serializer = ExpenseCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(ExpenseCategory, pk=pk, is_deleted=False)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class IncomeCategoryAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(IncomeCategory, pk=pk, is_deleted=False)
            serializer = IncomeCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = IncomeCategory.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = IncomeCategorySerializer(categories, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = IncomeCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        category = get_object_or_404(IncomeCategory, pk=pk, is_deleted=False)
        serializer = IncomeCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(IncomeCategory, pk=pk, is_deleted=False)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class DocumentTypeAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            doc_type = get_object_or_404(DocumentType, pk=pk, is_deleted=False)
            serializer = DocumentTypeSerializer(doc_type)
            return Response(serializer.data)
        else:
            doc_types = DocumentType.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                doc_types = doc_types.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = DocumentTypeSerializer(doc_types, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = DocumentTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        doc_type = get_object_or_404(DocumentType, pk=pk, is_deleted=False)
        serializer = DocumentTypeSerializer(doc_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        doc_type = get_object_or_404(DocumentType, pk=pk, is_deleted=False)
        doc_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class WorkTypeAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            work_type = get_object_or_404(WorkType, pk=pk, is_deleted=False)
            serializer = WorkTypeSerializer(work_type)
            return Response(serializer.data)
        else:
            work_types = WorkType.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                work_types = work_types.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = WorkTypeSerializer(work_types, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = WorkTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        work_type = get_object_or_404(WorkType, pk=pk, is_deleted=False)
        serializer = WorkTypeSerializer(work_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        work_type = get_object_or_404(WorkType, pk=pk, is_deleted=False)
        work_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class MaterialCategoryAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(MaterialCategory, pk=pk, is_deleted=False)
            serializer = MaterialCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = MaterialCategory.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = MaterialCategorySerializer(categories, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = MaterialCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        category = get_object_or_404(MaterialCategory, pk=pk, is_deleted=False)
        serializer = MaterialCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(MaterialCategory, pk=pk, is_deleted=False)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ToolCategoryAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(ToolCategory, pk=pk, is_deleted=False)
            serializer = ToolCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = ToolCategory.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = ToolCategorySerializer(categories, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = ToolCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        category = get_object_or_404(ToolCategory, pk=pk, is_deleted=False)
        serializer = ToolCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(ToolCategory, pk=pk, is_deleted=False)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class UnitTypeAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            unit_type = get_object_or_404(UnitType, pk=pk, is_deleted=False)
            serializer = UnitTypeSerializer(unit_type)
            return Response(serializer.data)
        else:
            unit_types = UnitType.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                unit_types = unit_types.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = UnitTypeSerializer(unit_types, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = UnitTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        unit_type = get_object_or_404(UnitType, pk=pk, is_deleted=False)
        serializer = UnitTypeSerializer(unit_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        unit_type = get_object_or_404(UnitType, pk=pk, is_deleted=False)
        unit_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class BrandAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            brand = get_object_or_404(Brand, pk=pk, is_deleted=False)
            serializer = BrandSerializer(brand)
            return Response(serializer.data)
        else:
            brands = Brand.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                brands = brands.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = BrandSerializer(brands, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = BrandSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk, is_deleted=False)
        serializer = BrandSerializer(brand, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk, is_deleted=False)
        brand.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class FinanceTypeAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            finance_type = get_object_or_404(FinanceType, pk=pk, is_deleted=False)
            serializer = FinanceTypeSerializer(finance_type)
            return Response(serializer.data)
        else:
            finance_types = FinanceType.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                finance_types = finance_types.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = FinanceTypeSerializer(finance_types, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = FinanceTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        finance_type = get_object_or_404(FinanceType, pk=pk, is_deleted=False)
        serializer = FinanceTypeSerializer(finance_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        finance_type = get_object_or_404(FinanceType, pk=pk, is_deleted=False)
        finance_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class PaymentViaAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            payment_via = get_object_or_404(PaymentVia, pk=pk, is_deleted=False)
            serializer = PaymentViaSerializer(payment_via)
            return Response(serializer.data)
        else:
            payment_vias = PaymentVia.objects.filter(is_deleted=False)
            search_query = request.query_params.get('search', None)
            if search_query:
                payment_vias = payment_vias.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            serializer = PaymentViaSerializer(payment_vias, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = PaymentViaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        payment_via = get_object_or_404(PaymentVia, pk=pk, is_deleted=False)
        serializer = PaymentViaSerializer(payment_via, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment_via = get_object_or_404(PaymentVia, pk=pk, is_deleted=False)
        payment_via.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)