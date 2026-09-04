from rest_framework import serializers
from .models import *
from project.models import *
from core.serializers import AuditModelSerializer, LocationSerializer
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from decouple import config

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        request = self.context.get('request')
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = request.build_absolute_uri(f'{config("BASE_URL")}reset-password-confirm/{uid}/{token}/')
        send_mail(
            'Password Reset Request',
            f'Click the link to reset your password: {reset_link}',
            'noreply@mmg-construction.com',
            [email],
            fail_silently=False,
        )

class ProjectSimpleSerializer(AuditModelSerializer):
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_superuser',
            'is_active',
            'is_staff',
            'date_joined',
            'last_login',
        ]


class ProfileSimpleSerializer(AuditModelSerializer):
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ('id', 'updated_at')


class ProfileDirectorySerializer(serializers.ModelSerializer):
    """Data profil yang aman untuk direktori internal seluruh staff."""

    class Meta:
        model = Profile
        fields = (
            'id',
            'full_name',
            'role',
            'gender',
            'phone_number',
            'profile_picture',
            'work_policy',
            'is_active',
        )
        read_only_fields = fields


class ProfileSelfUpdateSerializer(serializers.ModelSerializer):
    """Field personal yang boleh diperbarui oleh pemilik profil."""

    class Meta:
        model = Profile
        fields = (
            'id',
            'profile_picture',
            'full_name',
            'gender',
            'birthday',
            'phone_number',
        )
        read_only_fields = ('id',)


class TeamSimpleSerializer(AuditModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class TeamMemberSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=Profile.objects.all(),
        write_only=True,
    )
    team = TeamSimpleSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(
        source='team',
        queryset=Team.objects.all(),
        write_only=True,
    )

    class Meta:
        model = TeamMember
        fields = '__all__'
        read_only_fields = (
            'id', 'timestamp',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class TeamSerializer(AuditModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class TeamSimpleSerializer(AuditModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=Profile.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Signature
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class InitialSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=Profile.objects.all(),
        write_only=True,
    )
    
    class Meta:
        model = Initial
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class NotificationSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=Profile.objects.all(),
        write_only=True,
    )
    
    class Meta:
        model = Notifications
        fields = '__all__'
        read_only_fields = (
            'id', 'sent_at',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class AttendanceSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=Profile.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'worked_minutes', 'overtime_minutes',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )


class AttendanceCheckInSerializer(serializers.Serializer):
    work_policy = serializers.PrimaryKeyRelatedField(
        queryset=WorkPolicy.objects.filter(is_active=True),
    )
    work_mode = serializers.ChoiceField(
        choices=AttendanceWorkMode.choices,
        default=AttendanceWorkMode.OFFICE,
    )
    photo_check_in = serializers.ImageField()


class AttendanceCheckOutSerializer(serializers.Serializer):
    photo_check_out = serializers.ImageField()

class SignatureOnLeaveRequestSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
    )
    
    class Meta:
        model = SignatureOnLeaveRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class LeaveRequestSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=Profile.objects.all(),
        write_only=True,
    )
    approved_by = ProfileSimpleSerializer(read_only=True)
    approved_by_id = serializers.PrimaryKeyRelatedField(
        source='approved_by',
        queryset=Profile.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    leave_request_signatures = SignatureOnLeaveRequestSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'approved_by', 'approved_by_id',
            'approved_date',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

    def validate(self, attrs):
        attrs.pop('approved_by', None)
        attrs.pop('approved_date', None)
        attrs.pop('status', None)
        return super().validate(attrs)

class LeaveRequestSimpleSerializer(AuditModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    approved_by = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'approved_by', 'approved_date',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class ProfileSerializer(AuditModelSerializer):
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=User.objects.all(),
        write_only=True,
    )
    team_members = TeamMemberSerializer(many=True, read_only=True)
    signatures = SignatureSerializer(many=True, read_only=True)
    initials = InitialSerializer(many=True, read_only=True)
    user_notifications = NotificationSerializer(many=True, read_only=True)
    user_attendance = AttendanceSerializer(many=True, read_only=True)
    user_leave_request = LeaveRequestSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ('id', 'updated_at')

class SubContractorWorkerSerializer(AuditModelSerializer):
    class Meta:
        model = SubContractorWorker
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SubContractorOnProjectSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    subcon_id = serializers.PrimaryKeyRelatedField(
        source='subcon',
        queryset=SubContractor.objects.all(),
        write_only=True,
    )
    class Meta:
        model = SubContractorOnProject
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SubContractorSerializer(AuditModelSerializer):
    locations = LocationSerializer(read_only=True)
    locations_id = serializers.PrimaryKeyRelatedField(
        source='locations',
        queryset=Location.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    workers = SubContractorWorkerSerializer(many=True, read_only=True)
    subcontractors_on_project = SubContractorOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = SubContractor
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SubContractorSimpleSerializer(AuditModelSerializer):
    locations = LocationSerializer(read_only=True)

    class Meta:
        model = SubContractor
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class AnnouncementSerializer(AuditModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')


class WorkPolicySerializer(AuditModelSerializer):
    class Meta:
        model = WorkPolicy
        fields = '__all__'
        read_only_fields = (
            'id',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )


class HolidaySerializer(AuditModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'
        read_only_fields = (
            'id',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )
