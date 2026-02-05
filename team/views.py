import json
from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point
from geopy.distance import geodesic
from datetime import timedelta
    
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username_or_email = request.data.get('email_or_username')
        password = request.data.get('password')

        # Cek apakah input berupa email atau username
        try:
            if '@' in username_or_email:
                user = User.objects.get(email=username_or_email)
                username = user.username
            else:
                username = username_or_email
        except User.DoesNotExist:
            return Response({"detail": "Invalid email or username"}, status=status.HTTP_400_BAD_REQUEST)

        # Autentikasi user dengan username dan password
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Generate token JWT
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        
class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset link has been sent to your email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordAPIView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        try:
            user = User.objects.get(pk=user_id)
            if not check_password(current_password, user.password):
                return Response({'success': False, 'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            user.save()
            return Response({'success': True})
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class ProfileModelViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
            
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('location', 'user') \
                           .prefetch_related('team_members', 'user_signatures', 'user_initial', 'user_notifications', 
                                             'user_attendance', 'user_leave_request')
        if self.action == 'list':
            search_query = self.request.query_params.get('search', None)
            role = self.request.query_params.get('role', None)
            gender = self.request.query_params.get('gender', None)
            status_ = self.request.query_params.get('status', None)
            is_employee = self.request.query_params.get('is_employee', None)
            is_active = self.request.query_params.get('is_active', None)
            birthday = self.request.query_params.get('birthday', None)
            join_date = self.request.query_params.get('join_date', None)
            query = Q()
            if search_query:
                query = Q(full_name__icontains=search_query) | Q(email__icontains=search_query) | Q(phone_number__icontains=search_query)
            if role:
                query &= Q(role__icontains=role)
            if gender:
                query &= Q(gender__icontains=gender)
            if status_:
                query &= Q(status__icontains=status_)
            if is_employee is not None:
                is_employee = is_employee.lower() in ['true', '1', 't']
                query &= ~Q(role__in=['Client', 'client'])
            if is_active is not None:
                is_active = is_active.lower() in ['true', '1', 't']
                query &= Q(is_active=is_active)
            if birthday:
                query &= Q(birthday=birthday)
            if join_date:
                query &= Q(join_date=join_date)
            queryset = queryset.filter(query).distinct().order_by('full_name')
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProfileSimpleSerializer
        return ProfileSerializer

    def create(self, request, *args, **kwargs):
        team_members = request.data.get('team_members', [])
        request.data.pop('team_members', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            for member in team_members:
                TeamMember.objects.create(user=profile, **member)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class TeamModelViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.prefetch_related('members', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search', None)
            query = Q()
            if search_query:
                query = Q(name__icontains=search_query) | Q(description__icontains=search_query)
            queryset = queryset.filter(query).distinct()
            return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TeamSimpleSerializer
        return TeamSerializer

    def create(self, request, *args, **kwargs):
        members = request.data.get('members', [])
        request.data.pop('members', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            team = serializer.save()
            for member in members:
                TeamMember.objects.create(team=team, **member)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class TeamMemberModelViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    
class SignatureModelViewSet(viewsets.ModelViewSet):
    queryset = Signature.objects.all()
    serializer_class = SignatureSerializer
    
class InitialModelViewSet(viewsets.ModelViewSet):
    queryset = Initial.objects.all()
    serializer_class = InitialSerializer

class NotificationModelViewSet(viewsets.ModelViewSet):
    queryset = Notifications.objects.all()
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-sent_at')
        queryset = queryset.select_related('user', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search', None)
            is_read = self.request.query_params.get('is_read', None)
            send_at = self.request.query_params.get('sent_at', None)
            query = Q()
            if search_query:
                query = Q(title__icontains=search_query) | Q(message__icontains=search_query)
            if is_read is not None:
                is_read = is_read.lower() in ['true', '1', 't']
                query &= Q(is_read=is_read)
            if send_at:
                query &= Q(sent_at=send_at)
            queryset = queryset.filter(query).distinct()
            return queryset
    
class SubContractorModelViewSet(viewsets.ModelViewSet):
    queryset = SubContractor.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('locations', ) \
                           .prefetch_related('subcons_worker', 'subcon_projects')
        if self.action == 'list':
            search_query = self.request.query_params.get('search', None)
            query = Q()
            if search_query:
                query = Q(name__icontains=search_query) | Q(locations__name__icontains=search_query) | Q(contact_person__icontains=search_query) | Q(contact_number__icontains=search_query) | Q(email__icontains=search_query) | Q(descriptions__icontains=search_query)
            queryset = queryset.filter(query).distinct()
            return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SubContractorSimpleSerializer
        return SubContractorSerializer

    def create(self, request, *args, **kwargs):
        workers = request.data.get('workers', [])
        request.data.pop('workers', None)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            subcontractor = serializer.save()
            for worker in workers:
                SubContractorWorker.objects.create(subcon=subcontractor, **worker)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SubContractorWorkerModelViewSet(viewsets.ModelViewSet):
    queryset = SubContractorWorker.objects.all()
    serializer_class = SubContractorWorkerSerializer
    
class SubContractorOnProjectModelViewSet(viewsets.ModelViewSet):
    queryset = SubContractorOnProject.objects.all()
    serializer_class = SubContractorOnProjectSerializer

class AttendanceModelViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('user', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search', None)
            user = self.request.query_params.get('user', None)
            date = self.request.query_params.get('date', None)
            status_ = self.request.query_params.get('status', None)
            is_all = self.request.query_params.get('is_all', None)

            query = Q()
            if search_query:
                query &= Q(user__full_name__icontains=search_query) | Q(status__icontains=search_query)
            if user:
                query &= Q(user__id=user)
            if date:
                query &= Q(date=date)
            if status_:
                query &= Q(status=status_)
            queryset = queryset.filter(query).distinct()
            if user:
                userData = get_object_or_404(Profile, pk=user)
                today = timezone.now().date()
                start_of_week = today - timedelta(days=today.weekday())  # Senin minggu ini
                end_of_week = start_of_week + timedelta(days=6)  # Minggu minggu ini
                
                if (userData.role.lower() == 'ceo' or userData.role.lower() == 'it') and is_all == 'true':
                    print('iniii')
                    queryset = queryset
                elif is_all == 'true':
                    queryset = queryset.filter(user=user).order_by('-date')
                else:
                    queryset = queryset.filter(user=user, date__gte=start_of_week, date__lte=end_of_week).order_by('-date')
            return queryset
        
def parse_geo_json(geo_data):
    """
    Menerima input dari Flutter GeoPoint.toJson().
    Bisa berupa String (karena multipart) atau Dict.
    Format: {"type": "Point", "coordinates": [long, lat]}
    """
    try:
        # 1. Jika dikirim sebagai string (common in multipart/form-data)
        if isinstance(geo_data, str):
            geo_data = json.loads(geo_data)
        
        # 2. Ambil coordinates [longitude, latitude]
        # Pastikan key 'coordinates' ada (sesuai GeoPoint.toJson Anda)
        coords = geo_data.get('coordinates')
        
        if coords and len(coords) == 2:
            # Point(longitude, latitude) -> Ingat urutannya X, Y
            return Point(float(coords[0]), float(coords[1]), srid=4326)
            
    except (ValueError, TypeError, json.JSONDecodeError, IndexError):
        return None
    return None

def validate_location(label, profile, project, latitude, longitude , radius=200):
    """Validasi apakah lokasi user berada dalam radius tertentu dari kantor."""
    if not latitude or not longitude:
        return False
    if label == 'Work From Home':
        office_coords = (profile.location.latitude, profile.location.longitude)
    elif label == 'Client Site' and project is not None:
        office_coords = (project.location.latitude, project.location.longitude)
    else:
        office_coords = (-8.653866713645598, 115.26167582162132)
    user_coords = (latitude, longitude)
    return geodesic(user_coords, office_coords).meters <= radius

class CheckInView(APIView):
    def post(self, request):
        raw_user_data = request.data.get('user')
        raw_check_in_location_label = request.data.get('check_in_location_label')
        project_id = request.data.get('project_id')
        try:
            # Jika user dikirim sebagai JSON String '{"id": "...", "name": ...}'
            if isinstance(raw_user_data, str):
                user_data = json.loads(raw_user_data)
                user_id = user_data['id']
            else:
                # Fallback jika ternyata sudah berbentuk dict (jarang terjadi di multipart)
                user_id = raw_user_data['id']
                
            profile = get_object_or_404(Profile, pk=user_id)

        except (ValueError, KeyError, TypeError):
             return Response({"error": "Data user tidak valid"}, status=status.HTTP_400_BAD_REQUEST)
        
        raw_location = request.data.get('check_in_location')
        location_point = parse_geo_json(raw_location)

        if not location_point:
            return Response(
                {"error": "Format lokasi tidak valid. Pastikan mengirim GeoJSON."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if project_id and project_id != "null":
            project = get_object_or_404(Project, pk=project_id)
        else:
            project = None

        if not validate_location(raw_check_in_location_label, profile, project, location_point.y, location_point.x):
            return Response({"error": "Anda berada di luar area kantor!"}, status=status.HTTP_400_BAD_REQUEST)
        
        photo = request.FILES.get('photo_check_in') # Sesuaikan key dengan frontend
        now = timezone.localtime()
        today = now.date()

        if Attendance.objects.filter(user=profile, date=today).exists():
            return Response({"error": "Anda sudah check-in hari ini."}, status=status.HTTP_400_BAD_REQUEST)

        attendance = Attendance.objects.create(
            user=profile,
            check_in=now,
            check_in_location=location_point, # Simpan objek Point
            check_in_location_label=raw_check_in_location_label,
            photo_check_in=photo
        )

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)

class CheckOutView(APIView):
    def post(self, request):
        raw_user_data = request.data.get('user')
        raw_check_out_location_label = request.data.get('check_out_location_label')
        project_id = request.data.get('project_id')
        try:
            # Jika user dikirim sebagai JSON String '{"id": "...", "name": ...}'
            if isinstance(raw_user_data, str):
                user_data = json.loads(raw_user_data)
                user_id = user_data['id']
            else:
                # Fallback jika ternyata sudah berbentuk dict (jarang terjadi di multipart)
                user_id = raw_user_data['id']
                
            profile = get_object_or_404(Profile, pk=user_id)

        except (ValueError, KeyError, TypeError):
             return Response({"error": "Data user tidak valid"}, status=status.HTTP_400_BAD_REQUEST)
        
        raw_location = request.data.get('check_out_location')
        location_point = parse_geo_json(raw_location)

        if not location_point:
            return Response(
                {"error": "Format lokasi tidak valid."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if project_id and project_id != "null":
            project = get_object_or_404(Project, pk=project_id)
        else:
            project = None

        if not validate_location(raw_check_out_location_label, profile, project, location_point.y, location_point.x):
            return Response({"error": "Anda berada di luar area kantor!"}, status=status.HTTP_400_BAD_REQUEST)

        photo = request.FILES.get('photo_check_out')

        now = timezone.localtime()
        today = now.date()

        try:
            attendance = Attendance.objects.get(user=profile, date=today)
        except Attendance.DoesNotExist:
            return Response({"error": "Anda belum check-in hari ini."}, status=status.HTTP_400_BAD_REQUEST)

        if attendance.check_out:
            return Response({"error": "Anda sudah check-out hari ini."}, status=status.HTTP_400_BAD_REQUEST)

        # Update data check-out
        attendance.check_out = now
        attendance.check_out_location = location_point # Simpan objek Point
        attendance.check_out_location_label = raw_check_out_location_label
        attendance.photo_check_out = photo
        
        # Logic status (Ontime/Late/Early) ditangani otomatis oleh method save() di Model
        attendance.save()

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)
    
class LeaveRequestModelViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('user', 'approved_by') \
                           .prefetch_related('leave_request_signatures', )
        if self.action == 'list':
            search_query = self.request.query_params.get('search', None)
            user = self.request.query_params.get('user', None)
            status_ = self.request.query_params.get('status', None)
            start_date = self.request.query_params.get('start_date', None)
            end_date = self.request.query_params.get('end_date', None)
            approved_date = self.request.query_params.get('approved_date', None)
            approved_by = self.request.query_params.get('approved_by', None)
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
            queryset = queryset.filter(query).distinct()
            return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LeaveRequestSimpleSerializer
        return LeaveRequestSerializer

class SignatureOnLeaveRequestModelViewSet(viewsets.ModelViewSet):
    queryset = SignatureOnLeaveRequest.objects.all()
    serializer_class = SignatureOnLeaveRequestSerializer
    
class AnnouncementModelViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer