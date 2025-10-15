from rest_framework import status
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q

class BillOfQuantityAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            boq = get_object_or_404(BillOfQuantity, pk=pk)
            serializer = BillOfQuantitySerializer(boq, context={'request': request})
        else:
            boqs = BillOfQuantity.objects.all()
            search_query = request.query_params.get('search_query', None)
            project_id = request.query_params.get('project', None)
            status_ = request.query_params.get('status', None)
            issue_date = request.query_params.get('issue_date', None)
            due_date = request.query_params.get('due_date', None)
            approval_required = request.query_params.get('approval_required', None)
            approval_level = request.query_params.get('approval_level', None)
            updated_by = request.query_params.get('updated_by', None)
            updated_at = request.query_params.get('updated_at', None)
            created_by = request.query_params.get('created_by', None)
            created_at = request.query_params.get('created_at', None)
            query = Q()
            if search_query:
                query &= Q(document_name__icontains=search_query) | Q(project__project_name__icontains=search_query)
            if project_id:
                query &= Q(project__id=project_id)
            if status_:
                query &= Q(status=status_)
            if issue_date:
                query &= Q(issue_date=issue_date)
            if due_date:
                query &= Q(due_date=due_date)
            if approval_required:
                query &= Q(approval_required=approval_required)
            if approval_level:
                query &= Q(approval_level=approval_level)
            if updated_by:
                query &= Q(updated_by__id=updated_by)
            if updated_at:
                query &= Q(updated_at=updated_at)
            if created_by:
                query &= Q(created_by__id=created_by)
            if created_at:
                query &= Q(created_at=created_at)
            boqs = boqs.filter(query).distinct()
            serializer = BillOfQuantitySerializer(boqs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        boq_versions = request.data.get('boq_versions', [])
        boq_signatures = request.data.get('boq_signatures', [])
        request.data.pop('boq_versions', None)
        request.data.pop('boq_signatures', None)
        serializer = BillOfQuantitySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            boq=serializer.save()
            for version in boq_versions:
                BillOfQuantityVersion.objects.create(boq=boq, **version)
            for signature in boq_signatures:
                SignatureOnBillOfQuantity.objects.create(boq=boq, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        boq = get_object_or_404(BillOfQuantity, pk=pk)
        serializer = BillOfQuantitySerializer(boq, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        boq = get_object_or_404(BillOfQuantity, pk=pk)
        boq.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class BillOfQuantityVersionAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            boq_version = get_object_or_404(BillOfQuantityVersion, pk=pk)
            serializer = BillOfQuantityVersionSerializer(boq_version, context={'request': request})
        else:
            boq_versions = BillOfQuantityVersion.objects.all()
            serializer = BillOfQuantityVersionSerializer(boq_versions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = BillOfQuantityVersionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        boq_version = get_object_or_404(BillOfQuantityVersion, pk=pk)
        serializer = BillOfQuantityVersionSerializer(boq_version, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        boq_version = get_object_or_404(BillOfQuantityVersion, pk=pk)
        boq_version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnBillOfQuantityAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnBillOfQuantity, pk=pk)
            serializer = SignatureOnBillOfQuantitySerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnBillOfQuantity.objects.all()
            serializer = SignatureOnBillOfQuantitySerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = SignatureOnBillOfQuantitySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnBillOfQuantity, pk=pk)
        serializer = SignatureOnBillOfQuantitySerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        signature = get_object_or_404(SignatureOnBillOfQuantity, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PaymentRequestAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            payment_request = get_object_or_404(PaymentRequest, pk=pk)
            serializer = PaymentRequestSerializer(payment_request, context={'request': request})
        else:
            payment_requests = PaymentRequest.objects.all()
            search_query = request.query_params.get('search_query', None)
            project_id = request.query_params.get('project', None)
            status_ = request.query_params.get('status', None)
            issue_date = request.query_params.get('issue_date', None)
            due_date = request.query_params.get('due_date', None)
            approval_required = request.query_params.get('approval_required', None)
            approval_level = request.query_params.get('approval_level', None)
            updated_by = request.query_params.get('updated_by', None)
            updated_at = request.query_params.get('updated_at', None)
            created_by = request.query_params.get('created_by', None)
            created_at = request.query_params.get('created_at', None)
            query = Q()
            if search_query:
                query &= Q(payment_name__icontains=search_query) | Q(project__project_name__icontains=search_query)
            if project_id:
                query &= Q(project__id=project_id)
            if status_:
                query &= Q(status=status_)
            if issue_date:
                query &= Q(issue_date=issue_date)
            if due_date:
                query &= Q(due_date=due_date)
            if approval_required:
                query &= Q(approval_required=approval_required)
            if approval_level:
                query &= Q(approval_level=approval_level)
            if updated_by:
                query &= Q(updated_by__id=updated_by)
            if updated_at:
                query &= Q(updated_at=updated_at)
            if created_by:
                query &= Q(created_by__id=created_by)
            if created_at:
                query &= Q(created_at=created_at)
            payment_requests = payment_requests.filter(query).distinct()
            serializer = PaymentRequestSerializer(payment_requests, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        payment_versions = request.data.get('payment_versions', [])
        payment_signatures = request.data.get('payment_request_signatures', [])
        request.data.pop('payment_versions', None)
        request.data.pop('payment_request_signatures', None)
        serializer = PaymentRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment_request=serializer.save()
            for version in payment_versions:
                PaymentRequestVersion.objects.create(payment_request=payment_request, **version)
            for signature in payment_signatures:
                SignatureOnPaymentRequest.objects.create(document=payment_request, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        payment_request = get_object_or_404(PaymentRequest, pk=pk)
        serializer = PaymentRequestSerializer(payment_request, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment_request = get_object_or_404(PaymentRequest, pk=pk)
        payment_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PaymentRequestVersionAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            payment_version = get_object_or_404(PaymentRequestVersion, pk=pk)
            serializer = PaymentRequestVersionSerializer(payment_version, context={'request': request})
        else:
            payment_versions = PaymentRequestVersion.objects.all()
            serializer = PaymentRequestVersionSerializer(payment_versions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = PaymentRequestVersionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        payment_version = get_object_or_404(PaymentRequestVersion, pk=pk)
        serializer = PaymentRequestVersionSerializer(payment_version, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment_version = get_object_or_404(PaymentRequestVersion, pk=pk)
        payment_version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnPaymentRequestAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnPaymentRequest, pk=pk)
            serializer = SignatureOnPaymentRequestSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnPaymentRequest.objects.all()
            serializer = SignatureOnPaymentRequestSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = SignatureOnPaymentRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnPaymentRequest, pk=pk)
        serializer = SignatureOnPaymentRequestSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        signature = get_object_or_404(SignatureOnPaymentRequest, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ExpenseOnProjectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            expense = get_object_or_404(ExpenseOnProject, pk=pk)
            serializer = ExpenseOnProjectSerializer(expense, context={'request': request})
        else:
            expenses = ExpenseOnProject.objects.all()
            search_query = request.query_params.get('search_query', None)
            project_id = request.query_params.get('project', None)
            date = request.query_params.get('date', None)
            total = request.query_params.get('total', None)
            updated_by = request.query_params.get('updated_by', None)
            updated_at = request.query_params.get('updated_at', None)
            created_by = request.query_params.get('created_by', None)
            created_at = request.query_params.get('created_at', None)
            query = Q()
            if search_query:
                query &= Q(notes__icontains=search_query) | Q(project__project_name__icontains=search_query)
            if project_id:
                query &= Q(project__id=project_id)
            if date:
                query &= Q(date=date)
            if total:
                query &= Q(total=total)
            if updated_by:
                query &= Q(updated_by__id=updated_by)
            if updated_at:
                query &= Q(updated_at=updated_at)
            if created_by:
                query &= Q(created_by__id=created_by)
            if created_at:
                query &= Q(created_at=created_at)
            expenses = expenses.filter(query).distinct()
            serializer = ExpenseOnProjectSerializer(expenses, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        expense_details = request.data.get('expense_detail', [])
        expense_materials = request.data.get('expense_material', [])
        request.data.pop('expense_detail', None)
        request.data.pop('expense_material', None)
        serializer = ExpenseOnProjectSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            expense=serializer.save()
            for detail in expense_details:
                ExpenseDetail.objects.create(expense=expense, **detail)
            for material in expense_materials:
                ExpenseForMaterial.objects.create(expense=expense, **material)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        expense = get_object_or_404(ExpenseOnProject, pk=pk)
        serializer = ExpenseOnProjectSerializer(expense, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        expense = get_object_or_404(ExpenseOnProject, pk=pk)
        expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ExpenseDetailAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            expense_detail = get_object_or_404(ExpenseDetail, pk=pk)
            serializer = ExpenseDetailSerializer(expense_detail, context={'request': request})
        else:
            expense_details = ExpenseDetail.objects.all()
            serializer = ExpenseDetailSerializer(expense_details, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = ExpenseDetailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        expense_detail = get_object_or_404(ExpenseDetail, pk=pk)
        serializer = ExpenseDetailSerializer(expense_detail, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        expense_detail = get_object_or_404(ExpenseDetail, pk=pk)
        expense_detail.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ExpenseForMaterialAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            expense_material = get_object_or_404(ExpenseForMaterial, pk=pk)
            serializer = ExpenseForMaterialSerializer(expense_material, context={'request': request})
        else:
            expense_materials = ExpenseForMaterial.objects.all()
            serializer = ExpenseForMaterialSerializer(expense_materials, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = ExpenseForMaterialSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        expense_material = get_object_or_404(ExpenseForMaterial, pk=pk)
        serializer = ExpenseForMaterialSerializer(expense_material, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        expense_material = get_object_or_404(ExpenseForMaterial, pk=pk)
        expense_material.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class FinanceDataAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            finance_data = get_object_or_404(FinanceData, pk=pk)
            serializer = FinanceDataSerializer(finance_data, context={'request': request})
        else:
            finance_data = FinanceData.objects.all()
            serializer = FinanceDataSerializer(finance_data, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = FinanceDataSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        finance_data = get_object_or_404(FinanceData, pk=pk)
        serializer = FinanceDataSerializer(finance_data, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        finance_data = get_object_or_404(FinanceData, pk=pk)
        finance_data.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PettyCashAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            petty_cash = get_object_or_404(PettyCash, pk=pk)
            serializer = PettyCashSerializer(petty_cash, context={'request': request})
        else:
            petty_cash_records = PettyCash.objects.all()
            serializer = PettyCashSerializer(petty_cash_records, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = PettyCashSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        petty_cash = get_object_or_404(PettyCash, pk=pk)
        serializer = PettyCashSerializer(petty_cash, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        petty_cash = get_object_or_404(PettyCash, pk=pk)
        petty_cash.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)