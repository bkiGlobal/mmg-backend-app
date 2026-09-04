from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from core.permissions import (
    MANAGEMENT_ROLES,
    PROJECT_WRITE_ROLES,
    ProjectScopedQuerysetMixin,
    RoleBasedPermission,
    has_any_role,
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


class ProjectAccessViewSet(
    ProjectScopedQuerysetMixin, viewsets.ModelViewSet
):
    permission_classes = [RoleBasedPermission]
    write_roles = PROJECT_WRITE_ROLES


class ProjectModelViewSet(ProjectAccessViewSet):
    project_lookup = 'pk'
    queryset = Project.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-start_date')
        queryset = queryset.select_related('location', 'client', 'team') \
                           .prefetch_related('project_documents', 'project_drawings', 'project_defect', 'error_on_project', 
                                             'work_method_project', 'project_boqs', 'project_payment_requests', 'project_expense', 
                                             'project_finance_data', 'project_petty_cash', 'project_material', 'project_tools', 'project_subcon')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project_status = self.request.query_params.get('project_status', None)
            client = self.request.query_params.get('client', None)
            team = self.request.query_params.get('team', None)
            start_date = self.request.query_params.get('start_date', None)
            end_date = self.request.query_params.get('end_date', None)
            query = Q()
            if search_query:
                query &= (Q(project_code__icontains=search_query) | Q(project_name__icontains=search_query) | 
                          Q(client__user__username__icontains=search_query) | Q(team__name__icontains=search_query) | 
                          Q(description__icontains=search_query))
            if project_status:
                query &= Q(project_status=project_status)
            if client:
                query &= Q(client=client)
            if team:
                query &= Q(team=team)
            if start_date:
                query &= Q(start_date=start_date)
            if end_date:
                query &= Q(end_date=end_date)
            queryset = queryset.filter(query).distinct()
        return queryset
        
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectSimpleSerializer
        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        if not has_any_role(
            request.user,
            MANAGEMENT_ROLES | {'sales', 'project_admin'},
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                'Hanya management, sales, atau project admin '
                'yang dapat membuat proyek.'
            )
        data = normalize_foreign_keys(
            request.data, ('location', 'client', 'team')
        )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        project = serializer.instance
        return Response(
            self.get_serializer(project).data,
            status=status.HTTP_201_CREATED,
        )

class DocumentModelViewSet(ProjectAccessViewSet):
    queryset = Document.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-issue_date')
        queryset = queryset.select_related('project', 'document_type') \
                           .prefetch_related('versions', 'document_signatures')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project = self.request.query_params.get('project', None)
            document_type = self.request.query_params.get('document_type', None)
            status_ = self.request.query_params.get('status', None)
            issue_date = self.request.query_params.get('issue_date', None)
            due_date = self.request.query_params.get('due_date', None)
            approval_required = self.request.query_params.get('approval_required', None)
            approval_level = self.request.query_params.get('approval_level', None)
            query = Q()
            if search_query:
                query &= Q(project__project_name__icontains=search_query) | Q(document_name__icontains=search_query)
            if project:
                query &= Q(project=project)
            if document_type:
                query &= Q(document_type=document_type)
            if status_:
                query &= Q(status=status_)
            if issue_date:
                query &= Q(issue_date=issue_date)
            if due_date:
                query &= Q(due_date=due_date)
            if approval_required is not None:
                query &= Q(
                    approval_required=approval_required.lower()
                    in ('true', '1', 't')
                )
            if approval_level:
                query &= Q(approval_level=approval_level)
            queryset = queryset.filter(query).distinct()
        return queryset
        
    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentSimpleSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        versions = request.data.get('versions', [])
        document_signatures = request.data.get('document_signatures', [])
        data = request.data.copy()
        data.pop('versions', None)
        data.pop('document_signatures', None)
        data = normalize_foreign_keys(
            data, ('project', 'document_type')
        )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            document = serializer.instance
            for version in versions:
                version_data = dict(version)
                version_data['document'] = document.pk
                child = DocumentVersionSerializer(data=version_data)
                child.is_valid(raise_exception=True)
                child.save()
            for signature in document_signatures:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['document'] = document.pk
                child = SignatureOnDocumentSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(document).data,
            status=status.HTTP_201_CREATED,
        )
    
class DocumentVersionModelViewSet(ProjectAccessViewSet):
    project_lookup = 'document__project_id'
    queryset = DocumentVersion.objects.all()
    serializer_class = DocumentVersionSerializer
    
class SignatureOnDocumentModelViewSet(ProjectAccessViewSet):
    project_lookup = 'document__project_id'
    queryset = SignatureOnDocument.objects.all()
    serializer_class = SignatureOnDocumentSerializer

class DrawingModelViewSet(ProjectAccessViewSet):
    queryset = Drawing.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-issue_date')
        queryset = queryset.select_related('project', 'drawing_type') \
                           .prefetch_related('drawing_versions', 'drawing_signatures')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project = self.request.query_params.get('project', None)
            drawing_type = self.request.query_params.get('drawing_type', None)
            status_ = self.request.query_params.get('status', None)
            issue_date = self.request.query_params.get('issue_date', None)
            due_date = self.request.query_params.get('due_date', None)
            query = Q()
            if search_query:
                query &= Q(document_name__icontains=search_query) | Q(project__project_name__icontains=search_query)
            if project:
                query &= Q(project=project)
            if drawing_type:
                query &= Q(drawing_type=drawing_type)
            if status_:
                query &= Q(status=status_)
            if issue_date:
                query &= Q(issue_date=issue_date)
            if due_date:
                query &= Q(due_date=due_date)
            queryset = queryset.filter(query).distinct()
        return queryset
        
    def get_serializer_class(self):
        if self.action == 'list':
            return DrawingSimpleSerializer
        return DrawingSerializer

    def create(self, request, *args, **kwargs):
        drawing_versions = request.data.get('drawing_versions', [])
        drawing_signatures = request.data.get('drawing_signatures', [])
        data = request.data.copy()
        data.pop('drawing_versions', None)
        data.pop('drawing_signatures', None)
        data = normalize_foreign_keys(
            data, ('project', 'drawing_type')
        )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            drawing = serializer.instance
            for version in drawing_versions:
                version_data = dict(version)
                version_data['drawing'] = drawing.pk
                child = DrawingVersionSerializer(data=version_data)
                child.is_valid(raise_exception=True)
                child.save()
            for signature in drawing_signatures:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['document'] = drawing.pk
                child = SignatureOnDrawingSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(drawing).data,
            status=status.HTTP_201_CREATED,
        )
    
class DrawingVersionModelViewSet(ProjectAccessViewSet):
    project_lookup = 'drawing__project_id'
    queryset = DrawingVersion.objects.all()
    serializer_class = DrawingVersionSerializer
    
class SignatureOnDrawingModelViewSet(ProjectAccessViewSet):
    project_lookup = 'document__project_id'
    queryset = SignatureOnDrawing.objects.all()
    serializer_class = SignatureOnDrawingSerializer
    
class DefectModelViewSet(ProjectAccessViewSet):
    queryset = Defect.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('project', ) \
                           .prefetch_related('defect_detail', 'defect_signature')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project = self.request.query_params.get('project', None)
            is_approved = self.request.query_params.get('is_approved', None)
            approved_at = self.request.query_params.get('approved_at', None)
            query = Q()
            if search_query:
                query &= Q(work_title__icontains=search_query) | Q(project__project_name__icontains=search_query)
            if project:
                query &= Q(project=project)
            if is_approved is not None:
                query &= Q(
                    is_approved=is_approved.lower() in ('true', '1', 't')
                )
            if approved_at:
                query &= Q(approved_at=approved_at)
            queryset = queryset.filter(query).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DefectSimpleSerializer
        return DefectSerializer

    def create(self, request, *args, **kwargs):
        defect_detail = request.data.get('defect_detail', [])
        defect_signature = request.data.get('defect_signature', [])
        data = request.data.copy()
        data.pop('defect_detail', None)
        data.pop('defect_signature', None)
        data = normalize_foreign_keys(data, ('project',))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            defect = serializer.instance
            for detail in defect_detail:
                detail_data = normalize_foreign_keys(
                    detail,
                    (
                        'initial_checklist_approval',
                        'final_checklist_approval',
                    ),
                )
                detail_data['deflect'] = defect.pk
                child = DefectDetailSerializer(data=detail_data)
                child.is_valid(raise_exception=True)
                child.save()
            for signature in defect_signature:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['deflect'] = defect.pk
                child = SignatureOnDeflectSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(defect).data,
            status=status.HTTP_201_CREATED,
        )
    
class DefectDetailModelViewSet(ProjectAccessViewSet):
    project_lookup = 'deflect__project_id'
    queryset = DefectDetail.objects.all()
    serializer_class = DefectDetailSerializer
    
class SignatureOnDeflectModelViewSet(ProjectAccessViewSet):
    project_lookup = 'deflect__project_id'
    queryset = SignatureOnDeflect.objects.all()
    serializer_class = SignatureOnDeflectSerializer
    
class ErrorLogModelViewSet(ProjectAccessViewSet):
    queryset = ErrorLog.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('project', 'work_type') \
                           .prefetch_related('error_detail', 'error_log_signature')
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project = self.request.query_params.get('project', None)
            error_type = self.request.query_params.get('error_type', None)
            periode_start = self.request.query_params.get('periode_start', None)
            periode_end = self.request.query_params.get('periode_end', None)
            query = Q()
            if search_query:
                query &= Q(project__project_name__icontains=search_query) | Q(document_number__icontains=search_query) | Q(notes__icontains=search_query)
            if project:
                query &= Q(project=project)
            if error_type:
                query &= Q(work_type=error_type)
            if periode_start:
                query &= Q(periode_start=periode_start)
            if periode_end:
                query &= Q(periode_end=periode_end)
            queryset = queryset.filter(query).distinct()
        return queryset

    def create(self, request, *args, **kwargs):
        error_detail = request.data.get('error_detail', [])
        error_log_signature = request.data.get('error_log_signature', [])
        data = request.data.copy()
        data.pop('error_detail', None)
        data.pop('error_log_signature', None)
        data = normalize_foreign_keys(
            data, ('project', 'work_type')
        )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            error_log = serializer.instance
            for detail in error_detail:
                detail_data = dict(detail)
                detail_data['error'] = error_log.pk
                child = ErrorLogDetailSerializer(data=detail_data)
                child.is_valid(raise_exception=True)
                child.save()
            for signature in error_log_signature:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['error'] = error_log.pk
                child = SignatureOnErrorLogSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(error_log).data,
            status=status.HTTP_201_CREATED,
        )
    
class ErrorLogDetailModelViewSet(ProjectAccessViewSet):
    project_lookup = 'error__project_id'
    queryset = ErrorLogDetail.objects.all()
    serializer_class = ErrorLogDetailSerializer
    
class SignatureOnErrorLogModelViewSet(ProjectAccessViewSet):
    project_lookup = 'error__project_id'
    queryset = SignatureOnErrorLog.objects.all()
    serializer_class = SignatureOnErrorLogSerializer

class ScheduleModelViewSet(ProjectAccessViewSet):
    project_lookup = 'boq_item__project_id'
    queryset = Schedule.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('boq_item', ) \
                           .prefetch_related('schedule_signature', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            duration_type = self.request.query_params.get('duration_type', None)
            status_ = self.request.query_params.get('status', None)
            start_date = self.request.query_params.get('start_date', None)
            end_date = self.request.query_params.get('end_date', None)
            query = Q()
            if search_query:
                query &= (
                    Q(boq_item__document_name__icontains=search_query)
                    | Q(notes__icontains=search_query)
                )
            if duration_type:
                query &= Q(duration_type=duration_type)
            if status_:
                query &= Q(status=status_)
            if start_date:
                query &= Q(start_date=start_date)
            if end_date:
                query &= Q(end_date=end_date)
            queryset = queryset.filter(query).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ScheduleSimpleSerializer
        return ScheduleSerializer

    def create(self, request, *args, **kwargs):
        schedule_signature = request.data.get('schedule_signature', [])
        data = request.data.copy()
        data.pop('schedule_signature', None)
        data = normalize_foreign_keys(data, ('boq_item',))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            schedule = serializer.instance
            for signature in schedule_signature:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['schedule'] = schedule.pk
                child = SignatureOnScheduleSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(schedule).data,
            status=status.HTTP_201_CREATED,
        )
    
class SignatureOnScheduleModelViewSet(ProjectAccessViewSet):
    project_lookup = 'schedule__boq_item__project_id'
    queryset = SignatureOnSchedule.objects.all()
    serializer_class = SignatureOnScheduleSerializer

class ProgressReportModelViewSet(ProjectAccessViewSet):
    project_lookup = 'boq_item__project_id'
    queryset = ProgressReport.objects.all()
    serializer_class = ProgressReportSerializer
            
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('boq_item', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            progress_number = self.request.query_params.get('progress_number', None)
            report_type = self.request.query_params.get('type', None)
            report_date = self.request.query_params.get('report_date', None)
            progress_percentage = self.request.query_params.get('progress_percentage', None)
            query = Q()
            if search_query:
                query &= (
                    Q(boq_item__document_name__icontains=search_query)
                    | Q(notes__icontains=search_query)
                )
            if progress_number:
                query &= Q(progress_number=progress_number)
            if report_type:
                query &= Q(type=report_type)
            if report_date:
                query &= Q(report_date=report_date)
            if progress_percentage:
                query &= Q(progress_percentage=progress_percentage)
            queryset = queryset.filter(query).distinct()
        return queryset

    def create(self, request, *args, **kwargs):
        data = normalize_foreign_keys(request.data, ('boq_item',))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        report = serializer.instance
        return Response(
            self.get_serializer(report).data,
            status=status.HTTP_201_CREATED,
        )
    
class WorkMethodModelViewSet(ProjectAccessViewSet):
    queryset = WorkMethod.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('project', ) \
                           .prefetch_related('work_method_signature', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search_query', None)
            project = self.request.query_params.get('project', None)
            query = Q()
            if search_query:
                query &= Q(work_title__icontains=search_query) | Q(document_number__icontains=search_query) | Q(notes__icontains=search_query)
            if project:
                query &= Q(project=project)
            queryset = queryset.filter(query).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WorkMethodSimpleSerializer
        return WorkMethodSerializer

    def create(self, request, *args, **kwargs):
        work_method_signature = request.data.get('work_method_signature', [])
        data = request.data.copy()
        data.pop('work_method_signature', None)
        data = normalize_foreign_keys(data, ('project',))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            work_method = serializer.instance
            for signature in work_method_signature:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['work_method'] = work_method.pk
                child = SignatureOnWorkMethodSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(work_method).data,
            status=status.HTTP_201_CREATED,
        )
    
class SignatureOnWorkMethodModelViewSet(ProjectAccessViewSet):
    project_lookup = 'work_method__project_id'
    queryset = SignatureOnWorkMethod.objects.all()
    serializer_class = SignatureOnWorkMethodSerializer
