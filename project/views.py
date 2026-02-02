from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db.models import Q

class ProjectModelViewSet(viewsets.ModelViewSet):
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
            start_date = self.request.query_params.get('project_status', None)
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

class DocumentModelViewSet(viewsets.ModelViewSet):
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
                status_ &= Q(status=status_)
            if issue_date:
                issue_date &= Q(issue_date=issue_date)
            if due_date:
                due_date &= Q(due_date=due_date)
            if approval_required:
                approval_required &= Q(approval_required=approval_required)
            if approval_level:
                approval_level &= Q(approval_level=approval_level)
            queryset = queryset.filter(query).distinct()
        return queryset
        
    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentSimpleSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        versions = request.data.get('versions', [])
        document_signatures = request.data.get('document_signatures', [])
        request.data.pop('versions', None)
        request.data.pop('document_signatures', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save()
            for version in versions:
                DocumentVersion.objects.create(document=document, **version)
            for signature in document_signatures:
                SignatureOnDocument.objects.create(document=document, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class DocumentVersionModelViewSet(viewsets.ModelViewSet):
    queryset = DocumentVersion.objects.all()
    serializer_class = DocumentVersionSerializer
    
class SignatureOnDocumentModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnDocument.objects.all()
    serializer_class = SignatureOnDocumentSerializer

class DrawingModelViewSet(viewsets.ModelViewSet):
    queryset = Drawing.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-issue_date')
        queryset = queryset.select_related('project', 'drawing_type') \
                           .prefetch_related('drawing_versions', 'drawing_signatures')
        if self.action == 'list':
            search_query = request.query_params.get('search_query', None)
            project = request.query_params.get('project', None)
            drawing_type = request.query_params.get('drawing_type', None)
            status_ = request.query_params.get('status', None)
            issue_date = request.query_params.get('issue_date', None)
            due_date = request.query_params.get('due_date', None)
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
        request.data.pop('drawing_versions', None)
        request.data.pop('drawing_signatures', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            drawing = serializer.save()
            for version in drawing_versions:
                DrawingVersion.objects.create(drawing=drawing, **version)
            for signature in drawing_signatures:
                SignatureOnDrawing.objects.create(document=drawing, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class DrawingVersionModelViewSet(viewsets.ModelViewSet):
    queryset = DrawingVersion.objects.all()
    serializer_class = DrawingVersionSerializer
    
class SignatureOnDrawingModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnDrawing.objects.all()
    serializer_class = SignatureOnDrawingSerializer
    
class DefectModelViewSet(viewsets.ModelViewSet):
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
            if is_approved:
                query &= Q(is_approved=is_approved)
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
        request.data.pop('defect_detail', None)
        request.data.pop('defect_signature', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            defect = serializer.save()
            for detail in defect_detail:
                DefectDetail.objects.create(deflect=defect, **detail)
            for signature in defect_signature:
                SignatureOnDeflect.objects.create(deflect=defect, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class DefectDetailModelViewSet(viewsets.ModelViewSet):
    queryset = DefectDetail.objects.all()
    serializer_class = DefectDetailSerializer
    
class SignatureOnDeflectModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnDeflect.objects.all()
    serializer_class = SignatureOnDeflectSerializer
    
class ErrorLogModelViewSet(viewsets.ModelViewSet):
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
                query &= Q(error_type=error_type)
            if periode_start:
                query &= Q(periode_start=periode_start)
            if periode_end:
                query &= Q(periode_end=periode_end)
            queryset = queryset.filter(query).distinct()
        return queryset

    def post(self, request):
        error_detail = request.data.get('error_detail', [])
        error_log_signature = request.data.get('error_log_signature', [])
        request.data.pop('error_detail', None)
        request.data.pop('error_log_signature', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            error_log = serializer.save()
            for detail in error_detail:
                ErrorLogDetail.objects.create(error=error_log, **detail)
            for signature in error_log_signature:
                SignatureOnErrorLog.objects.create(error=error_log, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ErrorLogDetailModelViewSet(viewsets.ModelViewSet):
    queryset = ErrorLogDetail.objects.all()
    serializer_class = ErrorLogDetailSerializer
    
class SignatureOnErrorLogModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnErrorLog.objects.all()
    serializer_class = SignatureOnErrorLogSerializer

class ScheduleModelViewSet(viewsets.ModelViewSet):
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
                query &= Q(boq_item__description__icontains=search_query) | Q(notes__icontains=search_query)
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

    def post(self, request):
        schedule_signature = request.data.get('schedule_signature', [])
        request.data.pop('schedule_signature', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            schedule = serializer.save()
            for signature in schedule_signature:
                SignatureOnSchedule.objects.create(schedule=schedule, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SignatureOnScheduleModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnSchedule.objects.all()
    serializer_class = SignatureOnScheduleSerializer

class ProgressReportModelViewSet(viewsets.ModelViewSet):
    queryset = ProgressReport.objects.all()
    serializer_class = ProgressReportSerializer
            
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('boq_item', )
        if self.action == 'list':
            search_query = request.query_params.get('search_query', None)
            progress_number = request.query_params.get('progress_number', None)
            type = request.query_params.get('type', None)
            report_date = request.query_params.get('report_date', None)
            progress_percentage = request.query_params.get('progress_percentage', None)
            query = Q()
            if search_query:
                query &= Q(boq_item__description__icontains=search_query) | Q(notes__icontains=search_query)
            if progress_number:
                query &= Q(progress_number=progress_number)
            if type:
                query &= Q(type=type)
            if report_date:
                query &= Q(report_date=report_date)
            if progress_percentage:
                query &= Q(progress_percentage=progress_percentage)
            queryset = queryset.filter(query).distinct()
        return queryset
    
class WorkMethodModelViewSet(viewsets.ModelViewSet):
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
        request.data.pop('work_method_signature', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            work_method = serializer.save()
            for signature in work_method_signature:
                SignatureOnWorkMethod.objects.create(work_method=work_method, **signature)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SignatureOnWorkMethodModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnWorkMethod.objects.all()
    serializer_class = SignatureOnWorkMethodSerializer