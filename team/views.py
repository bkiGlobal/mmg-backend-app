import json
from rest_framework import status, viewsets
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.db.models import Q
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point
from datetime import timedelta
from core.permissions import (
    MANAGEMENT_ROLES,
    PEOPLE_WRITE_ROLES,
    PROJECT_WRITE_ROLES,
    ProjectScopedQuerysetMixin,
    RoleBasedPermission,
    accessible_project_ids,
    has_any_role,
)
from team.services import (
    get_effective_work_policy,
    validate_attendance_location,
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


class PeopleAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleBasedPermission]
    write_roles = PEOPLE_WRITE_ROLES


def is_people_manager(user):
    return has_any_role(user, PEOPLE_WRITE_ROLES)
    
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username_or_email = request.data.get('email_or_username')
        password = request.data.get('password')
        if not username_or_email or not password:
            return Response(
                {'detail': 'Email/username dan password wajib diisi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not request.user.is_authenticated:
            return Response(
                {'success': False, 'error': 'Authentication required.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user = request.user
        if not check_password(current_password or '', user.password):
            return Response(
                {
                    'success': False,
                    'error': 'Current password is incorrect',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not new_password:
            return Response(
                {'success': False, 'error': 'New password is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({'success': True})

class ProfileModelViewSet(PeopleAdminViewSet):
    queryset = Profile.objects.all()
    # Semua user terautentikasi dapat memperbarui profilnya sendiri.
    # Otorisasi object-level diterapkan pada update di bawah.
    write_roles = None

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related(
            'location',
            'user',
            'work_policy',
        )
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
                query = (
                    Q(full_name__icontains=search_query)
                    | Q(user__email__icontains=search_query)
                    | Q(phone_number__icontains=search_query)
                )
            if role:
                query &= Q(role__icontains=role)
            if gender:
                query &= Q(gender__icontains=gender)
            if status_:
                query &= Q(status__icontains=status_)
            if is_employee is not None:
                is_employee = is_employee.lower() in ['true', '1', 't']
                if is_employee:
                    query &= ~Q(role=RoleType.CLIENT)
                else:
                    query &= Q(role=RoleType.CLIENT)
            if is_active is not None:
                is_active = is_active.lower() in ['true', '1', 't']
                query &= Q(is_active=is_active)
            if birthday:
                query &= Q(birthday=birthday)
            if join_date:
                query &= Q(join_date=join_date)
            queryset = queryset.filter(query).distinct().order_by('full_name')
        return queryset

    def _is_own_profile_pk(self):
        profile = getattr(self.request.user, 'profile', None)
        return bool(
            profile
            and str(profile.pk) == str(self.kwargs.get('pk'))
        )

    def get_serializer_class(self):
        if self.action == 'list':
            if self.request.user.is_superuser:
                return ProfileSimpleSerializer
            return ProfileDirectorySerializer
        if self.action in {'update', 'partial_update'}:
            if self.request.user.is_superuser:
                return ProfileSerializer
            return ProfileSelfUpdateSerializer
        if (
            self.action == 'retrieve'
            and not self.request.user.is_superuser
            and not self._is_own_profile_pk()
        ):
            return ProfileDirectorySerializer
        return ProfileSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if (
            not request.user.is_superuser
            and instance.user_id != request.user.pk
        ):
            raise PermissionDenied(
                'Anda hanya dapat mengubah profile milik sendiri.'
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if (
            not request.user.is_superuser
            and instance.user_id != request.user.pk
        ):
            raise PermissionDenied(
                'Anda hanya dapat mengubah profile milik sendiri.'
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied(
                'Hanya superuser yang dapat menghapus profile.'
            )
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied(
                'Hanya superuser yang dapat membuat profile.'
            )
        team_members = request.data.get('team_members', [])
        data = request.data.copy()
        data.pop('team_members', None)
        data = normalize_foreign_keys(data, ('location', 'user'))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            profile = serializer.save()
            for member in team_members:
                member_data = normalize_foreign_keys(member, ('team',))
                member_data['user_id'] = profile.pk
                child = TeamMemberSerializer(data=member_data)
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(profile).data,
            status=status.HTTP_201_CREATED,
        )
    
class TeamModelViewSet(PeopleAdminViewSet):
    queryset = Team.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.prefetch_related('members', )
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(
                members__user__user=self.request.user,
                members__is_active=True,
            )
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
        data = request.data.copy()
        data.pop('members', None)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            team = serializer.save()
            for member in members:
                member_data = normalize_foreign_keys(member, ('user',))
                member_data['team_id'] = team.pk
                child = TeamMemberSerializer(data=member_data)
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(team).data,
            status=status.HTTP_201_CREATED,
        )
    
class TeamMemberModelViewSet(PeopleAdminViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('team', 'user')
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(
                team__members__user__user=self.request.user
            )
        return queryset.distinct()
    
class SignatureModelViewSet(PeopleAdminViewSet):
    write_roles = None
    queryset = Signature.objects.all()
    serializer_class = SignatureSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(user__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.profile)
    
class InitialModelViewSet(PeopleAdminViewSet):
    write_roles = None
    queryset = Initial.objects.all()
    serializer_class = InitialSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(user__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.profile)

class NotificationModelViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleBasedPermission]
    queryset = Notifications.objects.all()
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-sent_at')
        queryset = queryset.select_related('user', )
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(user__user=self.request.user)
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

    def perform_create(self, serializer):
        if not is_people_manager(self.request.user):
            raise PermissionDenied('Hanya admin yang dapat membuat notifikasi.')
        serializer.save()

    def perform_destroy(self, instance):
        if not is_people_manager(self.request.user):
            raise PermissionDenied('Notifikasi tidak dapat dihapus.')
        instance.delete(user=self.request.user)

    def perform_update(self, serializer):
        if (
            not is_people_manager(self.request.user)
            and serializer.instance.user.user_id != self.request.user.id
        ):
            raise PermissionDenied('Notifikasi ini bukan milik Anda.')
        allowed = {'is_read'}
        if not is_people_manager(self.request.user):
            unexpected = set(serializer.validated_data) - allowed
            if unexpected:
                raise PermissionDenied(
                    'User hanya dapat mengubah status baca notifikasi.'
                )
        serializer.save()
    
class SubContractorModelViewSet(PeopleAdminViewSet):
    write_roles = PROJECT_WRITE_ROLES
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
        data = request.data.copy()
        data.pop('workers', None)
        data = normalize_foreign_keys(data, ('locations',))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            subcontractor = serializer.save()
            for worker in workers:
                worker_data = dict(worker)
                worker_data['subcon'] = subcontractor.pk
                child = SubContractorWorkerSerializer(data=worker_data)
                child.is_valid(raise_exception=True)
                child.save()
        return Response(
            self.get_serializer(subcontractor).data,
            status=status.HTTP_201_CREATED,
        )
    
class SubContractorWorkerModelViewSet(PeopleAdminViewSet):
    write_roles = PROJECT_WRITE_ROLES
    queryset = SubContractorWorker.objects.all()
    serializer_class = SubContractorWorkerSerializer
    
class SubContractorOnProjectModelViewSet(
    ProjectScopedQuerysetMixin, PeopleAdminViewSet
):
    write_roles = PROJECT_WRITE_ROLES
    queryset = SubContractorOnProject.objects.all()
    serializer_class = SubContractorOnProjectSerializer

class AttendanceModelViewSet(PeopleAdminViewSet):
    # Mutasi generik hanya untuk superuser. User biasa menggunakan endpoint
    # checkin/checkout yang field-nya sengaja dibuat minimum.
    write_roles = ()
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related(
            'user',
            'user__location',
            'work_policy',
            'work_policy__office_location',
        )
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(user__user=self.request.user)
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
                userData = get_object_or_404(Profile, pk=user)
                if userData.role.lower() != 'ceo' and userData.role.lower() != 'cfo' and userData.role.lower() != 'it':
                    query &= Q(user__id=user)
            if date:
                query &= Q(date=date)
            if status_:
                query &= Q(status=status_)
            queryset = queryset.filter(query).distinct()
            if user:
                today = timezone.now().date()
                start_of_week = today - timedelta(days=today.weekday())  # Senin minggu ini
                end_of_week = start_of_week + timedelta(days=6)  # Minggu minggu ini
                
                if (userData.role.lower() == 'ceo' or userData.role.lower() == 'cfo' or userData.role.lower() == 'it') and is_all == 'true':
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

def parse_location_accuracy(raw_accuracy):
    if raw_accuracy in (None, ''):
        return None
    try:
        accuracy = float(raw_accuracy)
    except (TypeError, ValueError):
        raise DjangoValidationError(
            'Akurasi GPS harus berupa angka dalam meter.'
        )
    if accuracy < 0:
        raise DjangoValidationError(
            'Akurasi GPS tidak boleh bernilai negatif.'
        )
    return accuracy

class CheckInView(APIView):
    def post(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile user tidak ditemukan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data.copy()
        if not payload.get('work_policy') and payload.get('work_policy_id'):
            payload['work_policy'] = payload.get('work_policy_id')
        serializer = AttendanceCheckInSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        work_policy = serializer.validated_data['work_policy']
        work_mode = serializer.validated_data['work_mode']
        photo = serializer.validated_data['photo_check_in']

        raw_location = request.data.get('check_in_location')
        if not raw_location:
            return Response(
                {
                    'error': (
                        'Lokasi GPS terkini wajib dikirim saat check-in.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        location_point = parse_geo_json(raw_location)
        if location_point is None:
            return Response(
                {'error': 'Format GPS check-in tidak valid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            location_result = validate_attendance_location(
                profile,
                work_policy,
                work_mode,
                location_point,
            )
            location_accuracy = parse_location_accuracy(
                request.data.get('check_in_accuracy_meters')
            )
        except DjangoValidationError as exc:
            return Response(
                {'error': exc.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        today = timezone.localdate()

        try:
            with transaction.atomic():
                Profile.objects.select_for_update().get(pk=profile.pk)
                attendance = Attendance.objects.select_for_update().filter(
                    user=profile, date=today
                ).first()
                if attendance and attendance.check_in:
                    return Response(
                        {"error": "Anda sudah check-in hari ini."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if attendance and attendance.status in {
                    AttendanceStatus.LEAVE,
                    AttendanceStatus.HOLYDAY,
                }:
                    return Response(
                        {
                            'error': (
                                'Absensi hari ini berstatus cuti/libur. '
                                'Hubungi superuser untuk koreksi.'
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                values = {
                    'check_in': now,
                    'check_in_location': location_result.current_point,
                    'check_in_location_label': location_result.label,
                    'check_in_accuracy_meters': location_accuracy,
                    'check_in_distance_meters': (
                        location_result.distance_meters
                    ),
                    'photo_check_in': photo,
                    'work_policy': work_policy,
                    'work_mode': work_mode,
                    'status_override': None,
                    'status_override_reason': '',
                }
                if attendance:
                    for field_name, value in values.items():
                        setattr(attendance, field_name, value)
                    attendance.save()
                else:
                    attendance = Attendance.objects.create(
                        user=profile,
                        date=today,
                        **values,
                    )
        except IntegrityError:
            return Response(
                {"error": "Anda sudah check-in hari ini."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)

class CheckOutView(APIView):
    def post(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile user tidak ditemukan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AttendanceCheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = serializer.validated_data['photo_check_out']

        now = timezone.now()
        today = timezone.localdate()

        with transaction.atomic():
            try:
                attendance = Attendance.objects.select_for_update().get(
                    user=profile,
                    date=today,
                )
            except Attendance.DoesNotExist:
                return Response(
                    {"error": "Anda belum check-in hari ini."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if attendance.check_out:
                return Response(
                    {"error": "Anda sudah check-out hari ini."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            work_policy = (
                attendance.work_policy
                or get_effective_work_policy(profile)
            )
            raw_location = request.data.get('check_out_location')
            if not raw_location:
                return Response(
                    {
                        'error': (
                            'Lokasi GPS terkini wajib dikirim saat '
                            'check-out.'
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            location_point = parse_geo_json(raw_location)
            if location_point is None:
                return Response(
                    {'error': 'Format GPS check-out tidak valid.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                location_result = validate_attendance_location(
                    profile,
                    work_policy,
                    attendance.work_mode,
                    location_point,
                )
                location_accuracy = parse_location_accuracy(
                    request.data.get('check_out_accuracy_meters')
                )
            except DjangoValidationError as exc:
                return Response(
                    {'error': exc.messages[0]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            attendance.check_out = now
            attendance.check_out_location = location_result.current_point
            attendance.check_out_location_label = location_result.label
            attendance.check_out_accuracy_meters = location_accuracy
            attendance.check_out_distance_meters = (
                location_result.distance_meters
            )
            attendance.photo_check_out = photo
            attendance.save()

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)
    
class LeaveRequestModelViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleBasedPermission]
    queryset = LeaveRequest.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        queryset = queryset.select_related('user', 'approved_by') \
                           .prefetch_related('leave_request_signatures', )
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(user__user=self.request.user)
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
    
    def create(self, request, *args, **kwargs):
        signatures = request.data.get('leave_request_signatures', [])
        data = request.data.copy()
        data.pop('leave_request_signatures', None)
        if not is_people_manager(request.user):
            data['user_id'] = request.user.profile.pk
            data.pop('user', None)
            data.pop('approved_by', None)
            data.pop('approved_by_id', None)
            data['status'] = LeaveStatus.PENDING
        data = normalize_foreign_keys(data, ('user', 'approved_by'))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            leave_request = serializer.save()
            for signature in signatures:
                signature_data = normalize_foreign_keys(
                    signature, ('signature',)
                )
                signature_data['leave_request'] = leave_request.pk
                child = SignatureOnLeaveRequestSerializer(
                    data=signature_data
                )
                child.is_valid(raise_exception=True)
                child.save()

        return Response(
            self.get_serializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )
        
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        if not is_people_manager(request.user):
            for field in (
                'user',
                'user_id',
                'status',
                'approved_by',
                'approved_by_id',
                'approved_date',
            ):
                data.pop(field, None)
        data = normalize_foreign_keys(data, ('user', 'approved_by'))
        serializer = self.get_serializer(
            instance,
            data=data,
            partial=kwargs.pop('partial', False),
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class SignatureOnLeaveRequestModelViewSet(PeopleAdminViewSet):
    queryset = SignatureOnLeaveRequest.objects.all()
    serializer_class = SignatureOnLeaveRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'leave_request__user', 'signature'
        )
        if not is_people_manager(self.request.user):
            queryset = queryset.filter(
                leave_request__user__user=self.request.user
            )
        return queryset
    
class AnnouncementModelViewSet(PeopleAdminViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer


class WorkPolicyModelViewSet(PeopleAdminViewSet):
    queryset = WorkPolicy.objects.all().order_by('name')
    serializer_class = WorkPolicySerializer


class HolidayModelViewSet(PeopleAdminViewSet):
    queryset = Holiday.objects.all().order_by('-date')
    serializer_class = HolidaySerializer
