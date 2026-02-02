from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db.models import Q

class BillOfQuantityModelViewSet(viewsets.ModelViewSet):
    queryset = BillOfQuantity.objects.all() # Queryset dasar

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-issue_date')
        queryset = queryset.select_related('project', ) \
                           .prefetch_related('boq_versions', 'boq_signatures', 'reports_boq')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project_id = self.request.query_params.get('project', None)
            status_ = self.request.query_params.get('status', None)
            issue_date = self.request.query_params.get('issue_date', None)
            due_date = self.request.query_params.get('due_date', None)
            approval_required = self.request.query_params.get('approval_required', None)
            approval_level = self.request.query_params.get('approval_level', None)
            updated_by = self.request.query_params.get('updated_by', None)
            updated_at = self.request.query_params.get('updated_at', None)
            created_by = self.request.query_params.get('created_by', None)
            created_at = self.request.query_params.get('created_at', None)
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
            queryset = queryset.filter(query).distinct()
            return queryset
        
    def get_serializer_class(self):
        if self.action == 'list':
            return BillOfQuantitySimpleSerializer
        return BillOfQuantitySerializer

    def create(self, request, *args, **kwargs):
        boq_versions = request.data.get('boq_versions', [])
        boq_signatures = request.data.get('boq_signatures', [])
        request.data.pop('boq_versions', None)
        request.data.pop('boq_signatures', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            boq=serializer.save()
            for version in boq_versions:
                BillOfQuantityVersion.objects.create(boq=boq, **version)
            for signature in boq_signatures:
                SignatureOnBillOfQuantity.objects.create(boq=boq, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class BillOfQuantityVersionModelViewSet(viewsets.ModelViewSet):
    queryset = BillOfQuantityVersion.objects.all()
    serializer_class = BillOfQuantityVersionSerializer
    
class SignatureOnBillOfQuantityModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnBillOfQuantity.objects.all()
    serializer_class = SignatureOnBillOfQuantitySerializer

class PaymentRequestModelViewSet(viewsets.ModelViewSet):
    queryset = PaymentRequest.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-issue_date')
        queryset = queryset.select_related('project', ) \
                           .prefetch_related('payment_versions', 'payment_request_signatures')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project_id = self.request.query_params.get('project', None)
            status_ = self.request.query_params.get('status', None)
            issue_date = self.request.query_params.get('issue_date', None)
            due_date = self.request.query_params.get('due_date', None)
            approval_required = self.request.query_params.get('approval_required', None)
            approval_level = self.request.query_params.get('approval_level', None)
            updated_by = self.request.query_params.get('updated_by', None)
            updated_at = self.request.query_params.get('updated_at', None)
            created_by = self.request.query_params.get('created_by', None)
            created_at = self.request.query_params.get('created_at', None)
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
            queryset = queryset.filter(query).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PaymentRequestSimpleSerializer
        return PaymentRequestSerializer
    
    def create(self, request, *args, **kwargs):
        payment_versions = request.data.get('payment_versions', [])
        payment_signatures = request.data.get('payment_request_signatures', [])
        request.data.pop('payment_versions', None)
        request.data.pop('payment_request_signatures', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment_request=serializer.save()
            for version in payment_versions:
                PaymentRequestVersion.objects.create(payment_request=payment_request, **version)
            for signature in payment_signatures:
                SignatureOnPaymentRequest.objects.create(document=payment_request, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentRequestVersionModelViewSet(viewsets.ModelViewSet):
    queryset = PaymentRequestVersion.objects.all()
    serializer_class = PaymentRequestVersionSerializer
    
class SignatureOnPaymentRequestModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnPaymentRequest.objects.all()
    serializer_class = SignatureOnPaymentRequestSerializer

class ExpenseOnProjectModelViewSet(viewsets.ModelViewSet):
    queryset = ExpenseOnProject.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-date')
        queryset = queryset.select_related('project', ) \
                           .prefetch_related('expense_detail', 'expense_material')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project_id = self.request.query_params.get('project', None)
            date = self.request.query_params.get('date', None)
            total = self.request.query_params.get('total', None)
            updated_by = self.request.query_params.get('updated_by', None)
            updated_at = self.request.query_params.get('updated_at', None)
            created_by = self.request.query_params.get('created_by', None)
            created_at = self.request.query_params.get('created_at', None)
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
            queryset = queryset.filter(query).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseOnProjectSimpleSerializer
        return ExpenseOnProjectSerializer

    def create(self, request, *args, **kwargs):
        expense_details = request.data.get('expense_detail', [])
        expense_materials = request.data.get('expense_material', [])
        request.data.pop('expense_detail', None)
        request.data.pop('expense_material', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            expense=serializer.save()
            for detail in expense_details:
                ExpenseDetail.objects.create(expense=expense, **detail)
            for material in expense_materials:
                ExpenseForMaterial.objects.create(expense=expense, **material)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExpenseDetailModelViewSet(viewsets.ModelViewSet):
    queryset = ExpenseDetail.objects.all()
    serializer_class = ExpenseDetailSerializer
    
class ExpenseForMaterialModelViewSet(viewsets.ModelViewSet):
    queryset = ExpenseForMaterial.objects.all()
    serializer_class = ExpenseForMaterialSerializer
    
class FinanceDataModelViewSet(viewsets.ModelViewSet):
    queryset = FinanceData.objects.all()
    serializer_class = FinanceDataSerializer

class PettyCashModelViewSet(viewsets.ModelViewSet):
    queryset = PettyCash.objects.all()
    serializer_class = PettyCashSerializer