from rest_framework import status
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q

class ProfileAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            profile = get_object_or_404(Profile, pk=pk)
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            profiles = Profile.objects.all()
            search_query = request.query_params.get('search', None)
            role = request.query_params.get('role', None)
            gender = request.query_params.get('gender', None)
            status_ = request.query_params.get('status', None)
            is_active = request.query_params.get('is_active', None)
            birthday = request.query_params.get('birthday', None)
            join_date = request.query_params.get('join_date', None)
            query = Q()
            if search_query:
                query = Q(full_name__icontains=search_query) | Q(email__icontains=search_query) | Q(phone_number__icontains=search_query)
            if role:
                query &= Q(role__icontains=role)
            if gender:
                query &= Q(gender__icontains=gender)
            if status_:
                query &= Q(status__icontains=status_)
            if is_active is not None:
                is_active = is_active.lower() in ['true', '1', 't']
                query &= Q(is_active=is_active)
            if birthday:
                query &= Q(birthday=birthday)
            if join_date:
                query &= Q(join_date=join_date)
            profiles = profiles.filter(query).distinct()
            serializer = ProfileSerializer(profiles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        team_members = request.data.get('team_members', [])
        request.data.pop('team_members', None)
        serializer = ProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            for member in team_members:
                TeamMember.objects.create(user=profile, **member)
            return Response(ProfileSerializer(profile).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            profile = serializer.save()
            return Response(ProfileSerializer(profile).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class TeamAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            team = get_object_or_404(Team, pk=pk)
            serializer = TeamSerializer(team)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            teams = Team.objects.all()
            search_query = request.query_params.get('search', None)
            query = Q()
            if search_query:
                query = Q(name__icontains=search_query) | Q(description__icontains=search_query)
            teams = teams.filter(query).distinct()
            serializer = TeamSerializer(teams, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        members = request.data.get('members', [])
        request.data.pop('members', None)
        serializer = TeamSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            team = serializer.save()
            for member in members:
                TeamMember.objects.create(team=team, **member)
            return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        serializer = TeamSerializer(team, data=request.data, partial=True)
        if serializer.is_valid():
            team = serializer.save()
            return Response(TeamSerializer(team).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        team.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class TeamMemberAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            team_member = get_object_or_404(TeamMember, pk=pk)
            serializer = TeamMemberSerializer(team_member)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            team_members = TeamMember.objects.all()
            serializer = TeamMemberSerializer(team_members, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeamMemberSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            team_member = serializer.save()
            return Response(TeamMemberSerializer(team_member).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        team_member = get_object_or_404(TeamMember, pk=pk)
        serializer = TeamMemberSerializer(team_member, data=request.data, partial=True)
        if serializer.is_valid():
            team_member = serializer.save()
            return Response(TeamMemberSerializer(team_member).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        team_member = get_object_or_404(TeamMember, pk=pk)
        team_member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SignatureAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(Signature, pk=pk)
            serializer = SignatureSerializer(signature)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            signatures = Signature.objects.all()
            serializer = SignatureSerializer(signatures, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureSerializer(signature).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        signature = get_object_or_404(Signature, pk=pk)
        serializer = SignatureSerializer(signature, data=request.data, partial=True)
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureSerializer(signature).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        signature = get_object_or_404(Signature, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class InitialAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            initial = get_object_or_404(Initial, pk=pk)
            serializer = InitialSerializer(initial)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            initials = Initial.objects.all()
            serializer = InitialSerializer(initials, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = InitialSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            initial = serializer.save()
            return Response(InitialSerializer(initial).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        initial = get_object_or_404(Initial, pk=pk)
        serializer = InitialSerializer(initial, data=request.data, partial=True)
        if serializer.is_valid():
            initial = serializer.save()
            return Response(InitialSerializer(initial).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        initial = get_object_or_404(Initial, pk=pk)
        initial.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class NotificationAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            notification = get_object_or_404(Notifications, pk=pk)
            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            notifications = Notifications.objects.all()
            search_query = request.query_params.get('search', None)
            is_read = request.query_params.get('is_read', None)
            send_at = request.query_params.get('sent_at', None)
            query = Q()
            if search_query:
                query = Q(title__icontains=search_query) | Q(message__icontains=search_query)
            if is_read is not None:
                is_read = is_read.lower() in ['true', '1', 't']
                query &= Q(is_read=is_read)
            if send_at:
                query &= Q(sent_at=send_at)
            notifications = notifications.filter(query).distinct()
            serializer = NotificationSerializer(notifications, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = NotificationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            notification = serializer.save()
            return Response(NotificationSerializer(notification).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        notification = get_object_or_404(Notifications, pk=pk)
        serializer = NotificationSerializer(notification, data=request.data, partial=True)
        if serializer.is_valid():
            notification = serializer.save()
            return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        notification = get_object_or_404(Notifications, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SubContractorAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            subcontractor = get_object_or_404(SubContractor, pk=pk)
            serializer = SubContractorSerializer(subcontractor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            subcontractors = SubContractor.objects.all()
            search_query = request.query_params.get('search', None)
            query = Q()
            if search_query:
                query = Q(name__icontains=search_query) | Q(locations__name__icontains=search_query) | Q(contact_person__icontains=search_query) | Q(contact_number__icontains=search_query) | Q(email__icontains=search_query) | Q(descriptions__icontains=search_query)
            subcontractors = subcontractors.filter(query).distinct()
            serializer = SubContractorSerializer(subcontractors, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        workers = request.data.get('workers', [])
        request.data.pop('workers', None)
        serializer = SubContractorSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            subcontractor = serializer.save()
            for worker in workers:
                SubContractorWorker.objects.create(subcon=subcontractor, **worker)
            return Response(SubContractorSerializer(subcontractor).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        subcontractor = get_object_or_404(SubContractor, pk=pk)
        serializer = SubContractorSerializer(subcontractor, data=request.data, partial=True)
        if serializer.is_valid():
            subcontractor = serializer.save()
            return Response(SubContractorSerializer(subcontractor).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        subcontractor = get_object_or_404(SubContractor, pk=pk)
        subcontractor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SubContractorWorkerAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            worker = get_object_or_404(SubContractorWorker, pk=pk)
            serializer = SubContractorWorkerSerializer(worker)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            workers = SubContractorWorker.objects.all()
            serializer = SubContractorWorkerSerializer(workers, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SubContractorWorkerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            worker = serializer.save()
            return Response(SubContractorWorkerSerializer(worker).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        worker = get_object_or_404(SubContractorWorker, pk=pk)
        serializer = SubContractorWorkerSerializer(worker, data=request.data, partial=True)
        if serializer.is_valid():
            worker = serializer.save()
            return Response(SubContractorWorkerSerializer(worker).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        worker = get_object_or_404(SubContractorWorker, pk=pk)
        worker.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class SubContractorOnProjectAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            subcontractor_on_project = get_object_or_404(SubContractorOnProject, pk=pk)
            serializer = SubContractorOnProjectSerializer(subcontractor_on_project)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            subcontractors_on_project = SubContractorOnProject.objects.all()
            serializer = SubContractorOnProjectSerializer(subcontractors_on_project, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SubContractorOnProjectSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            subcontractor_on_project = serializer.save()
            return Response(SubContractorOnProjectSerializer(subcontractor_on_project).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        subcontractor_on_project = get_object_or_404(SubContractorOnProject, pk=pk)
        serializer = SubContractorOnProjectSerializer(subcontractor_on_project, data=request.data, partial=True)
        if serializer.is_valid():
            subcontractor_on_project = serializer.save()
            return Response(SubContractorOnProjectSerializer(subcontractor_on_project).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        subcontractor_on_project = get_object_or_404(SubContractorOnProject, pk=pk)
        subcontractor_on_project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AttendanceAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            attendance = get_object_or_404(Attendance, pk=pk)
            serializer = AttendanceSerializer(attendance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            attendances = Attendance.objects.all()
            search_query = request.query_params.get('search', None)
            user = request.query_params.get('user', None)
            date = request.query_params.get('date', None)
            status_ = request.query_params.get('status', None)
            query = Q()
            if search_query:
                query &= Q(user__full_name__icontains=search_query) | Q(status__icontains=search_query)
            if user:
                query &= Q(user__id=user)
            if date:
                query &= Q(date=date)
            if status_:
                query &= Q(status=status_)
            attendances = attendances.filter(query).distinct()
            serializer = AttendanceSerializer(attendances, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AttendanceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            attendance = serializer.save()
            return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        attendance = get_object_or_404(Attendance, pk=pk)
        serializer = AttendanceSerializer(attendance, data=request.data, partial=True)
        if serializer.is_valid():
            attendance = serializer.save()
            return Response(AttendanceSerializer(attendance).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        attendance = get_object_or_404(Attendance, pk=pk)
        attendance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class LeaveRequestAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            leave_request = get_object_or_404(LeaveRequest, pk=pk)
            serializer = LeaveRequestSerializer(leave_request)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            leave_requests = LeaveRequest.objects.all()
            search_query = request.query_params.get('search', None)
            user = request.query_params.get('user', None)
            status_ = request.query_params.get('status', None)
            start_date = request.query_params.get('start_date', None)
            end_date = request.query_params.get('end_date', None)
            approved_date = request.query_params.get('approved_date', None)
            approved_by = request.query_params.get('approved_by', None)
            query = Q()
            if search_query:
                query &= Q(user__full_name__icontains=search_query) | Q(reason__icontains=search_query)
            if user:
                query &= Q(user__id=user)
            if status_:
                query &= Q(status=status_)
            if start_date:
                query &= Q(start_date=start_date)
            if end_date:
                query &= Q(end_date=end_date)
            if approved_date:
                query &= Q(approved_date=approved_date)
            if approved_by:
                query &= Q(approved_by__id=approved_by)
            leave_requests = leave_requests.filter(query).distinct()
            serializer = LeaveRequestSerializer(leave_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            leave_request = serializer.save()
            return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        serializer = LeaveRequestSerializer(leave_request, data=request.data, partial=True)
        if serializer.is_valid():
            leave_request = serializer.save()
            return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        leave_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SignatureOnLeaveRequestAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            signature = get_object_or_404(SignatureOnLeaveRequest, pk=pk)
            serializer = SignatureOnLeaveRequestSerializer(signature)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            signatures = SignatureOnLeaveRequest.objects.all()
            serializer = SignatureOnLeaveRequestSerializer(signatures, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignatureOnLeaveRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnLeaveRequestSerializer(signature).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        signature = get_object_or_404(SignatureOnLeaveRequest, pk=pk)
        serializer = SignatureOnLeaveRequestSerializer(signature, data=request.data, partial=True)
        if serializer.is_valid():
            signature = serializer.save()
            return Response(SignatureOnLeaveRequestSerializer(signature).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        signature = get_object_or_404(SignatureOnLeaveRequest, pk=pk)
        signature.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)