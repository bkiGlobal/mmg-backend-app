from rest_framework import status
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q

class ProjectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            project = get_object_or_404(Project, pk=pk)
            serializer = ProjectSerializer(project, context={'request': request})
        else:
            projects = Project.objects.all()
            search_query = request.query_params.get('search_query', None)
            project_status = request.query_params.get('project_status', None)
            client = request.query_params.get('client', None)
            team = request.query_params.get('team', None)
            start_date = request.query_params.get('project_status', None)
            end_date = request.query_params.get('end_date', None)
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
            projects = projects.filter(query).distinct()
            serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProjectSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            project = serializer.save()
            return Response(ProjectSerializer(project, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = ProjectSerializer(project, data=request.data, context={'request': request})
        if serializer.is_valid():
            project = serializer.save()
            return Response(ProjectSerializer(project, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        project = get_object_or_404(Project, pk=pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DocumentAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            document = get_object_or_404(Document, pk=pk)
            serializer = DocumentSerializer(document, context={'request': request})
        else:
            documents = Document.objects.all()
            search_query = request.query_params.get('search_query', None)
            project = request.query_params.get('project', None)
            document_type = request.query_params.get('document_type', None)
            status_ = request.query_params.get('status', None)
            issue_date = request.query_params.get('issue_date', None)
            due_date = request.query_params.get('due_date', None)
            approval_required = request.query_params.get('approval_required', None)
            approval_level = request.query_params.get('approval_level', None)
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
            documents = documents.filter(query).distinct()
            serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        versions = request.data.get('versions', [])
        document_signatures = request.data.get('document_signatures', [])
        request.data.pop('versions', None)
        request.data.pop('document_signatures', None)
        serializer = DocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save()
            for version in versions:
                DocumentVersion.objects.create(document=document, **version)
            for signature in document_signatures:
                SignatureOnDocument.objects.create(document=document, **signature)
            return Response(DocumentSerializer(document, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        serializer = DocumentSerializer(document, data=request.data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save()
            return Response(DocumentSerializer(document, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        document = get_object_or_404(Document, pk=pk)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class DocumentVersionAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            document_version = get_object_or_404(DocumentVersion, pk=pk)
            serializer = DocumentVersionSerializer(document_version, context={'request': request})
        else:
            document_versions = DocumentVersion.objects.all()
            serializer = DocumentVersionSerializer(document_versions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DocumentVersionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            document_version = serializer.save()
            return Response(DocumentVersionSerializer(document_version, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        document_version = get_object_or_404(DocumentVersion, pk=pk)
        serializer = DocumentVersionSerializer(document_version, data=request.data, context={'request': request})
        if serializer.is_valid():
            document_version = serializer.save()
            return Response(DocumentVersionSerializer(document_version, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        document_version = get_object_or_404(DocumentVersion, pk=pk)
        document_version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnDocumentAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnDocument, pk=pk)
            serializer = SignatureOnDocumentSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnDocument.objects.all()
            serializer = SignatureOnDocumentSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnDocumentSerializer(signature, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnDocument, pk=pk)
        serializer = SignatureOnDocumentSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnDocumentSerializer(signature, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        signature = get_object_or_404(SignatureOnDocument, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DrawingAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            drawing = get_object_or_404(Drawing, pk=pk)
            serializer = DrawingSerializer(drawing, context={'request': request})
        else:
            drawings = Drawing.objects.all()
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
            drawings = drawings.filter(query).distinct()
            serializer = DrawingSerializer(drawings, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        drawing_versions = request.data.get('drawing_versions', [])
        drawing_signatures = request.data.get('drawing_signatures', [])
        request.data.pop('drawing_versions', None)
        request.data.pop('drawing_signatures', None)
        serializer = DrawingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            drawing = serializer.save()
            for version in drawing_versions:
                DrawingVersion.objects.create(drawing=drawing, **version)
            for signature in drawing_signatures:
                SignatureOnDrawing.objects.create(document=drawing, **signature)
            return Response(DrawingSerializer(drawing, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        drawing = get_object_or_404(Drawing, pk=pk)
        serializer = DrawingSerializer(drawing, data=request.data, context={'request': request})
        if serializer.is_valid():
            drawing = serializer.save()
            return Response(DrawingSerializer(drawing, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        drawing = get_object_or_404(Drawing, pk=pk)
        drawing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class DrawingVersionAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            drawing_version = get_object_or_404(DrawingVersion, pk=pk)
            serializer = DrawingVersionSerializer(drawing_version, context={'request': request})
        else:
            drawing_versions = DrawingVersion.objects.all()
            serializer = DrawingVersionSerializer(drawing_versions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DrawingVersionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            drawing_version = serializer.save()
            return Response(DrawingVersionSerializer(drawing_version, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        drawing_version = get_object_or_404(DrawingVersion, pk=pk)
        serializer = DrawingVersionSerializer(drawing_version, data=request.data, context={'request': request})
        if serializer.is_valid():
            drawing_version = serializer.save()
            return Response(DrawingVersionSerializer(drawing_version, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        drawing_version = get_object_or_404(DrawingVersion, pk=pk)
        drawing_version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnDrawingAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnDrawing, pk=pk)
            serializer = SignatureOnDrawingSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnDrawing.objects.all()
            serializer = SignatureOnDrawingSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnDrawingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnDrawingSerializer(signature, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnDrawing, pk=pk)
        serializer = SignatureOnDrawingSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnDrawingSerializer(signature, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        signature = get_object_or_404(SignatureOnDrawing, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class DefectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            defect = get_object_or_404(Defect, pk=pk)
            serializer = DefectSerializer(defect, context={'request': request})
        else:
            defects = Defect.objects.all()
            search_query = request.query_params.get('search_query', None)
            project = request.query_params.get('project', None)
            is_approved = request.query_params.get('is_approved', None)
            approved_at = request.query_params.get('approved_at', None)
            query = Q()
            if search_query:
                query &= Q(work_title__icontains=search_query) | Q(project__project_name__icontains=search_query)
            if project:
                query &= Q(project=project)
            if is_approved:
                query &= Q(is_approved=is_approved)
            if approved_at:
                query &= Q(approved_at=approved_at)
            defects = defects.filter(query).distinct()
            serializer = DefectSerializer(defects, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        defect_detail = request.data.get('defect_detail', [])
        defect_signature = request.data.get('defect_signature', [])
        request.data.pop('defect_detail', None)
        request.data.pop('defect_signature', None)
        serializer = DefectSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            defect = serializer.save()
            for detail in defect_detail:
                DefectDetail.objects.create(deflect=defect, **detail)
            for signature in defect_signature:
                SignatureOnDeflect.objects.create(deflect=defect, **signature)
            return Response(DefectSerializer(defect, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        defect = get_object_or_404(Defect, pk=pk)
        serializer = DefectSerializer(defect, data=request.data, context={'request': request})
        if serializer.is_valid():
            defect = serializer.save()
            return Response(DefectSerializer(defect, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        defect = get_object_or_404(Defect, pk=pk)
        defect.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class DefectDetailAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            defect_detail = get_object_or_404(DefectDetail, pk=pk)
            serializer = DefectDetailSerializer(defect_detail, context={'request': request})
        else:
            defect_details = DefectDetail.objects.all()
            serializer = DefectDetailSerializer(defect_details, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DefectDetailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            defect_detail = serializer.save()
            return Response(DefectDetailSerializer(defect_detail, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        defect_detail = get_object_or_404(DefectDetail, pk=pk)
        serializer = DefectDetailSerializer(defect_detail, data=request.data, context={'request': request})
        if serializer.is_valid():
            defect_detail = serializer.save()
            return Response(DefectDetailSerializer(defect_detail, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        defect_detail = get_object_or_404(DefectDetail, pk=pk)
        defect_detail.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnDeflectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnDeflect, pk=pk)
            serializer = SignatureOnDeflectSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnDeflect.objects.all()
            serializer = SignatureOnDeflectSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnDeflectSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnDeflectSerializer(signature, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnDeflect, pk=pk)
        serializer = SignatureOnDeflectSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnDeflectSerializer(signature, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        signature = get_object_or_404(SignatureOnDeflect, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ErrorLogAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            error_log = get_object_or_404(ErrorLog, pk=pk)
            serializer = ErrorLogSerializer(error_log, context={'request': request})
        else:
            error_logs = ErrorLog.objects.all()
            search_query = request.query_params.get('search_query', None)
            project = request.query_params.get('project', None)
            error_type = request.query_params.get('error_type', None)
            periode_start = request.query_params.get('periode_start', None)
            periode_end = request.query_params.get('periode_end', None)
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
            error_logs = error_logs.filter(query).distinct()    
            serializer = ErrorLogSerializer(error_logs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        error_detail = request.data.get('error_detail', [])
        error_log_signature = request.data.get('error_log_signature', [])
        request.data.pop('error_detail', None)
        request.data.pop('error_log_signature', None)
        serializer = ErrorLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            error_log = serializer.save()
            for detail in error_detail:
                ErrorLogDetail.objects.create(error=error_log, **detail)
            for signature in error_log_signature:
                SignatureOnErrorLog.objects.create(error=error_log, **signature)
            return Response(ErrorLogSerializer(error_log, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        error_log = get_object_or_404(ErrorLog, pk=pk)
        serializer = ErrorLogSerializer(error_log, data=request.data, context={'request': request})
        if serializer.is_valid():
            error_log = serializer.save()
            return Response(ErrorLogSerializer(error_log, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        error_log = get_object_or_404(ErrorLog, pk=pk)
        error_log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ErrorLogDetailAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            error_log_detail = get_object_or_404(ErrorLogDetail, pk=pk)
            serializer = ErrorLogDetailSerializer(error_log_detail, context={'request': request})
        else:
            error_log_details = ErrorLogDetail.objects.all()
            serializer = ErrorLogDetailSerializer(error_log_details, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ErrorLogDetailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            error_log_detail = serializer.save()
            return Response(ErrorLogDetailSerializer(error_log_detail, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        error_log_detail = get_object_or_404(ErrorLogDetail, pk=pk)
        serializer = ErrorLogDetailSerializer(error_log_detail, data=request.data, context={'request': request})
        if serializer.is_valid():
            error_log_detail = serializer.save()
            return Response(ErrorLogDetailSerializer(error_log_detail, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        error_log_detail = get_object_or_404(ErrorLogDetail, pk=pk)
        error_log_detail.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnErrorLogAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnErrorLog, pk=pk)
            serializer = SignatureOnErrorLogSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnErrorLog.objects.all()
            serializer = SignatureOnErrorLogSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnErrorLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnErrorLogSerializer(signature, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnErrorLog, pk=pk)
        serializer = SignatureOnErrorLogSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnErrorLogSerializer(signature, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        signature = get_object_or_404(SignatureOnErrorLog, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ScheduleAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            schedule = get_object_or_404(Schedule, pk=pk)
            serializer = ScheduleSerializer(schedule, context={'request': request})
        else:
            schedules = Schedule.objects.all()
            search_query = request.query_params.get('search_query', None)
            duration_type = request.query_params.get('duration_type', None)
            status_ = request.query_params.get('status', None)
            start_date = request.query_params.get('start_date', None)
            end_date = request.query_params.get('end_date', None)
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
            schedules = schedules.filter(query).distinct()
            serializer = ScheduleSerializer(schedules, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        schedule_signature = request.data.get('schedule_signature', [])
        request.data.pop('schedule_signature', None)
        serializer = ScheduleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            schedule = serializer.save()
            for signature in schedule_signature:
                SignatureOnSchedule.objects.create(schedule=schedule, **signature)
            return Response(ScheduleSerializer(schedule, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        schedule = get_object_or_404(Schedule, pk=pk)
        serializer = ScheduleSerializer(schedule, data=request.data, context={'request': request})
        if serializer.is_valid():
            schedule = serializer.save()
            return Response(ScheduleSerializer(schedule, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        schedule = get_object_or_404(Schedule, pk=pk)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnScheduleAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnSchedule, pk=pk)
            serializer = SignatureOnScheduleSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnSchedule.objects.all()
            serializer = SignatureOnScheduleSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnScheduleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnScheduleSerializer(signature, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnSchedule, pk=pk)
        serializer = SignatureOnScheduleSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnScheduleSerializer(signature, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        signature = get_object_or_404(SignatureOnSchedule, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProgressReportAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            report = get_object_or_404(ProgressReport, pk=pk)
            serializer = ProgressReportSerializer(report, context={'request': request})
        else:
            reports = ProgressReport.objects.all()
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
            reports = reports.filter(query).distinct()
            serializer = ProgressReportSerializer(reports, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProgressReportSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            report = serializer.save()
            return Response(ProgressReportSerializer(report, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        report = get_object_or_404(ProgressReport, pk=pk)
        serializer = ProgressReportSerializer(report, data=request.data, context={'request': request})
        if serializer.is_valid():
            report = serializer.save()
            return Response(ProgressReportSerializer(report, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        report = get_object_or_404(ProgressReport, pk=pk)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class WorkMethodAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            work_method = get_object_or_404(WorkMethod, pk=pk)
            serializer = WorkMethodSerializer(work_method, context={'request': request})
        else:
            work_methods = WorkMethod.objects.all()
            search_query = request.query_params.get('search_query', None)
            project = request.query_params.get('project', None)
            query = Q()
            if search_query:
                query &= Q(work_title__icontains=search_query) | Q(document_number__icontains=search_query) | Q(notes__icontains=search_query)
            if project:
                query &= Q(project=project)
            work_methods = work_methods.filter(query).distinct()
            serializer = WorkMethodSerializer(work_methods, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        work_method_signature = request.data.get('work_method_signature', [])
        request.data.pop('work_method_signature', None)
        serializer = WorkMethodSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            work_method = serializer.save()
            for signature in work_method_signature:
                SignatureOnWorkMethod.objects.create(work_method=work_method, **signature)
            return Response(WorkMethodSerializer(work_method, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        work_method = get_object_or_404(WorkMethod, pk=pk)
        serializer = WorkMethodSerializer(work_method, data=request.data, context={'request': request})
        if serializer.is_valid():
            work_method = serializer.save()
            return Response(WorkMethodSerializer(work_method, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        work_method = get_object_or_404(WorkMethod, pk=pk)
        work_method.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureOnWorkMethodAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnWorkMethod, pk=pk)
            serializer = SignatureOnWorkMethodSerializer(signature, context={'request': request})
        else:
            signatures = SignatureOnWorkMethod.objects.all()
            serializer = SignatureOnWorkMethodSerializer(signatures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnWorkMethodSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnWorkMethodSerializer(signature, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnWorkMethod, pk=pk)
        serializer = SignatureOnWorkMethodSerializer(signature, data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnWorkMethodSerializer(signature, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk): 
        signature = get_object_or_404(SignatureOnWorkMethod, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)