from rest_framework import status
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
import logging
from rest_framework.permissions import AllowAny
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from core.permissions import (
    APPROVAL_ROLES,
    MANAGEMENT_ROLES,
    RoleBasedPermission,
    accessible_project_ids,
    has_any_role,
)
from core.workflows import decide_approval, submit_for_approval

logger = logging.getLogger(__name__)


class LookupAPIView(APIView):
    permission_classes = [RoleBasedPermission]
    write_roles = MANAGEMENT_ROLES

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom Refresh View untuk debugging kenapa refresh gagal
    """
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            # Cek validitas token
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # INI PENTING: Tangkap error spesifik SimpleJWT
            # Seringkali errornya adalah "Token is blacklisted" atau "Token is invalid"
            logger.error(f"Refresh Token Gagal: {e}")
            return Response(
                {"detail": "Refresh token tidak valid atau sudah kadaluarsa.", "code": "token_not_valid", "error_debug": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Jika sukses, kembalikan response standar
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class LocationAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            location = get_object_or_404(Location, pk=pk)
            serializer = LocationSerializer(location)
            return Response(serializer.data)
        else:
            locations = Location.objects.all()
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
        location = get_object_or_404(Location, pk=pk)
        serializer = LocationSerializer(location, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        location = get_object_or_404(Location, pk=pk)
        location.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ExpenseCategoryAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(ExpenseCategory, pk=pk)
            serializer = ExpenseCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = ExpenseCategory.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query)
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
        category = get_object_or_404(ExpenseCategory, pk=pk)
        serializer = ExpenseCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(ExpenseCategory, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class IncomeCategoryAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(IncomeCategory, pk=pk)
            serializer = IncomeCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = IncomeCategory.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query)
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
        category = get_object_or_404(IncomeCategory, pk=pk)
        serializer = IncomeCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(IncomeCategory, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class DocumentTypeAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            doc_type = get_object_or_404(DocumentType, pk=pk)
            serializer = DocumentTypeSerializer(doc_type)
            return Response(serializer.data)
        else:
            doc_types = DocumentType.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                doc_types = doc_types.filter(
                    Q(name__icontains=search_query)
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
        doc_type = get_object_or_404(DocumentType, pk=pk)
        serializer = DocumentTypeSerializer(doc_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        doc_type = get_object_or_404(DocumentType, pk=pk)
        doc_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class WorkTypeAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            work_type = get_object_or_404(WorkType, pk=pk)
            serializer = WorkTypeSerializer(work_type)
            return Response(serializer.data)
        else:
            work_types = WorkType.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                work_types = work_types.filter(
                    Q(name__icontains=search_query)
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
        work_type = get_object_or_404(WorkType, pk=pk)
        serializer = WorkTypeSerializer(work_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        work_type = get_object_or_404(WorkType, pk=pk)
        work_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class MaterialCategoryAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(MaterialCategory, pk=pk)
            serializer = MaterialCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = MaterialCategory.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query)
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
        category = get_object_or_404(MaterialCategory, pk=pk)
        serializer = MaterialCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(MaterialCategory, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ToolCategoryAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(ToolCategory, pk=pk)
            serializer = ToolCategorySerializer(category)
            return Response(serializer.data)
        else:
            categories = ToolCategory.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                categories = categories.filter(
                    Q(name__icontains=search_query)
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
        category = get_object_or_404(ToolCategory, pk=pk)
        serializer = ToolCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(ToolCategory, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class UnitTypeAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            unit_type = get_object_or_404(UnitType, pk=pk)
            serializer = UnitTypeSerializer(unit_type)
            return Response(serializer.data)
        else:
            unit_types = UnitType.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                unit_types = unit_types.filter(
                    Q(name__icontains=search_query)
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
        unit_type = get_object_or_404(UnitType, pk=pk)
        serializer = UnitTypeSerializer(unit_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        unit_type = get_object_or_404(UnitType, pk=pk)
        unit_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class BrandAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            brand = get_object_or_404(Brand, pk=pk)
            serializer = BrandSerializer(brand)
            return Response(serializer.data)
        else:
            brands = Brand.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                brands = brands.filter(
                    Q(name__icontains=search_query)
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
        brand = get_object_or_404(Brand, pk=pk)
        serializer = BrandSerializer(brand, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        brand.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class FinanceTypeAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            finance_type = get_object_or_404(FinanceType, pk=pk)
            serializer = FinanceTypeSerializer(finance_type)
            return Response(serializer.data)
        else:
            finance_types = FinanceType.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                finance_types = finance_types.filter(
                    Q(name__icontains=search_query)
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
        finance_type = get_object_or_404(FinanceType, pk=pk)
        serializer = FinanceTypeSerializer(finance_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        finance_type = get_object_or_404(FinanceType, pk=pk)
        finance_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class PaymentViaAPIView(LookupAPIView):
    def get(self, request, pk=None):
        if pk:
            payment_via = get_object_or_404(PaymentVia, pk=pk)
            serializer = PaymentViaSerializer(payment_via)
            return Response(serializer.data)
        else:
            payment_vias = PaymentVia.objects.all()
            search_query = request.query_params.get('search', None)
            if search_query:
                payment_vias = payment_vias.filter(
                    Q(name__icontains=search_query)
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
        payment_via = get_object_or_404(PaymentVia, pk=pk)
        serializer = PaymentViaSerializer(payment_via, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment_via = get_object_or_404(PaymentVia, pk=pk)
        payment_via.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


APPROVAL_TARGETS = {
    'finance.billofquantity': ('Bill of Quantity', 'qs,cfo'),
    'finance.paymentrequest': ('Payment Request', 'cfo,finance_admin'),
    'project.document': ('Project Document', 'pm,project_admin'),
    'project.drawing': ('Drawing', 'pm,architect'),
    'team.leaverequest': ('Leave Request', 'admin,ceo,project_admin'),
    'inventory.materialonproject': (
        'Material Approval',
        'logistic,pm,project_admin',
    ),
    'inventory.purchaserequest': (
        'Purchase Request',
        'logistic,cfo,pm',
    ),
}


def _target_project_id(target):
    if target._meta.label_lower == 'team.leaverequest':
        return None
    if hasattr(target, 'project_id'):
        return target.project_id
    if hasattr(target, 'boq_item'):
        return target.boq_item.project_id
    return None


def _can_access_approval_target(user, target):
    if has_any_role(user, MANAGEMENT_ROLES):
        return True
    label = target._meta.label_lower
    if label == 'team.leaverequest':
        return (
            target.user.user_id == user.id
            or has_any_role(user, {'project_admin'})
        )
    if label.startswith('finance.') and has_any_role(
        user, {'cfo', 'finance_admin'}
    ):
        return True
    if label.startswith('inventory.') and has_any_role(
        user, {'logistic'}
    ):
        return True
    project_id = _target_project_id(target)
    if project_id is None:
        return False
    allowed_ids = accessible_project_ids(user)
    return allowed_ids is None or project_id in set(allowed_ids)


class ApprovalQueueAPIView(APIView):
    def get(self, request):
        queryset = ApprovalRequest.objects.select_related(
            'content_type',
            'requested_by',
            'decided_by',
        ).prefetch_related('events')
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if not has_any_role(request.user, APPROVAL_ROLES):
            queryset = queryset.filter(requested_by=request.user)
        elif not has_any_role(request.user, MANAGEMENT_ROLES):
            from core.workflows import user_can_decide

            visible_ids = []
            for approval in queryset:
                target = approval.content_object
                if (
                    approval.requested_by_id == request.user.id
                    or (
                        target is not None
                        and user_can_decide(request.user, approval)
                        and _can_access_approval_target(
                            request.user, target
                        )
                    )
                ):
                    visible_ids.append(approval.pk)
            queryset = queryset.filter(pk__in=visible_ids)
        return Response(
            ApprovalRequestSerializer(queryset, many=True).data
        )

    def post(self, request):
        app_label = request.data.get('app_label')
        model = request.data.get('model')
        object_id = request.data.get('object_id')
        label = f'{app_label}.{model}'.lower()
        configuration = APPROVAL_TARGETS.get(label)
        if not configuration:
            return Response(
                {'detail': 'Tipe objek tidak mendukung approval.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        content_type = get_object_or_404(
            ContentType,
            app_label=app_label,
            model=model.lower(),
        )
        target = get_object_or_404(
            content_type.model_class().objects.all(),
            pk=object_id,
        )
        if not _can_access_approval_target(request.user, target):
            raise PermissionDenied('Anda tidak dapat mengakses objek ini.')
        try:
            approval = submit_for_approval(
                target,
                request.user,
                workflow_type=configuration[0],
                required_role=configuration[1],
                comment=request.data.get('comment', ''),
            )
        except ValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, 'message_dict')
                else exc.messages
            )
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ApprovalRequestSerializer(approval).data,
            status=status.HTTP_201_CREATED,
        )


class ApprovalDecisionAPIView(APIView):
    def post(self, request, pk, decision):
        approval = get_object_or_404(ApprovalRequest, pk=pk)
        if decision not in {'approve', 'reject'}:
            return Response(
                {'detail': 'Decision harus approve atau reject.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target = approval.content_object
        if (
            target is None
            or not _can_access_approval_target(request.user, target)
        ):
            raise PermissionDenied(
                'Anda tidak dapat mengakses objek approval ini.'
            )
        try:
            approval = decide_approval(
                approval,
                request.user,
                approve=decision == 'approve',
                comment=request.data.get('comment', ''),
            )
        except ValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, 'message_dict')
                else exc.messages
            )
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalRequestSerializer(approval).data)
