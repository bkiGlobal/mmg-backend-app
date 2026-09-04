from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from core.permissions import (
    FINANCE_WRITE_ROLES,
    ProjectScopedQuerysetMixin,
    RoleBasedPermission,
)


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


class FinanceProjectViewSet(
    ProjectScopedQuerysetMixin, viewsets.ModelViewSet
):
    permission_classes = [RoleBasedPermission]
    write_roles = FINANCE_WRITE_ROLES
    global_project_roles = {'cfo', 'finance_admin'}


class BillOfQuantityModelViewSet(FinanceProjectViewSet):
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
        data = request.data.copy()
        data.pop('boq_versions', None)
        data.pop('boq_signatures', None)
        data = normalize_foreign_keys(data, ('project',))
        serializer = self.get_serializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            self.perform_create(serializer)
            boq = serializer.instance
            for version in boq_versions:
                version_data = dict(version)
                version_data['boq'] = boq.pk
                version_serializer = BillOfQuantityVersionSerializer(
                    data=version_data,
                    context={'request': request},
                )
                version_serializer.is_valid(raise_exception=True)
                version_serializer.save()
            for signature in boq_signatures:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['boq'] = boq.pk
                signature_serializer = (
                    SignatureOnBillOfQuantitySerializer(
                        data=signature_data,
                        context={'request': request},
                    )
                )
                signature_serializer.is_valid(raise_exception=True)
                signature_serializer.save()

        return Response(
            self.get_serializer(boq).data,
            status=status.HTTP_201_CREATED,
        )
    
class BillOfQuantityVersionModelViewSet(FinanceProjectViewSet):
    project_lookup = 'boq__project_id'
    queryset = BillOfQuantityVersion.objects.all()
    serializer_class = BillOfQuantityVersionSerializer
    
class SignatureOnBillOfQuantityModelViewSet(FinanceProjectViewSet):
    project_lookup = 'boq__project_id'
    queryset = SignatureOnBillOfQuantity.objects.all()
    serializer_class = SignatureOnBillOfQuantitySerializer

class PaymentRequestModelViewSet(FinanceProjectViewSet):
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
        data = request.data.copy()
        data.pop('payment_versions', None)
        data.pop('payment_request_signatures', None)
        data = normalize_foreign_keys(data, ('project',))
        serializer = self.get_serializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            self.perform_create(serializer)
            payment_request = serializer.instance
            for version in payment_versions:
                version_data = dict(version)
                version_data['payment_request'] = payment_request.pk
                version_serializer = PaymentRequestVersionSerializer(
                    data=version_data,
                    context={'request': request},
                )
                version_serializer.is_valid(raise_exception=True)
                version_serializer.save()
            for signature in payment_signatures:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['document'] = payment_request.pk
                signature_serializer = SignatureOnPaymentRequestSerializer(
                    data=signature_data,
                    context={'request': request},
                )
                signature_serializer.is_valid(raise_exception=True)
                signature_serializer.save()

        return Response(
            self.get_serializer(payment_request).data,
            status=status.HTTP_201_CREATED,
        )

class PaymentRequestVersionModelViewSet(FinanceProjectViewSet):
    project_lookup = 'payment_request__project_id'
    queryset = PaymentRequestVersion.objects.all()
    serializer_class = PaymentRequestVersionSerializer
    
class SignatureOnPaymentRequestModelViewSet(FinanceProjectViewSet):
    project_lookup = 'document__project_id'
    queryset = SignatureOnPaymentRequest.objects.all()
    serializer_class = SignatureOnPaymentRequestSerializer

class ExpenseOnProjectModelViewSet(FinanceProjectViewSet):
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

        data = request.data.copy()
        data.pop('expense_detail', None)
        data.pop('expense_material', None)
        if 'project' in data and 'project_id' not in data:
            data['project_id'] = data.get('project')
            data.pop('project')

        serializer = self.get_serializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            self.perform_create(serializer)
            expense = serializer.instance

            for detail in expense_details:
                detail_data = normalize_foreign_keys(
                    detail, ('category', 'unit')
                )
                detail_data['expense'] = expense.pk
                detail_serializer = ExpenseDetailSerializer(
                    data=detail_data,
                    context={
                        'request': request,
                        'recalculate': False,
                    },
                )
                detail_serializer.is_valid(raise_exception=True)
                detail_serializer.save()

            for material in expense_materials:
                material_data = normalize_foreign_keys(
                    material, ('material', 'category', 'unit')
                )
                material_data['expense'] = expense.pk
                material_serializer = ExpenseForMaterialSerializer(
                    data=material_data,
                    context={
                        'request': request,
                        'recalculate': False,
                    },
                )
                material_serializer.is_valid(raise_exception=True)
                material_serializer.save()

            expense.recalculate_total()

        response_serializer = self.get_serializer(expense)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

class ExpenseDetailModelViewSet(FinanceProjectViewSet):
    project_lookup = 'expense__project_id'
    queryset = ExpenseDetail.objects.all()
    serializer_class = ExpenseDetailSerializer
    
class ExpenseForMaterialModelViewSet(FinanceProjectViewSet):
    project_lookup = 'expense__project_id'
    queryset = ExpenseForMaterial.objects.all()
    serializer_class = ExpenseForMaterialSerializer
    
class FinanceDataModelViewSet(FinanceProjectViewSet):
    queryset = FinanceData.objects.all()
    serializer_class = FinanceDataSerializer

class PettyCashModelViewSet(FinanceProjectViewSet):
    queryset = PettyCash.objects.all()
    serializer_class = PettyCashSerializer
