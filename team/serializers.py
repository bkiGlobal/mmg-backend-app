from rest_framework import serializers
from .models import *
from project.models import *
from core.serializers import LocationSerializer
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

class ProjectSimpleSerializer(serializers.ModelSerializer):
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


class ProfileSimpleSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ('id', 'updated_at')

class TeamSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class TeamMemberSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    team = TeamSimpleSerializer(read_only=True)

    class Meta:
        model = TeamMember
        fields = '__all__'
        read_only_fields = ('id', 'timestamp')

class TeamSerializer(serializers.ModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class TeamSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = Signature
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class InitialSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    
    class Meta:
        model = Initial
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class NotificationSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    
    class Meta:
        model = Notifications
        fields = '__all__'
        read_only_fields = ('id', 'sent_at')

class AttendanceSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnLeaveRequestSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)
    
    class Meta:
        model = SignatureOnLeaveRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class LeaveRequestSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    approved_by = ProfileSimpleSerializer(read_only=True)
    leave_request_signatures = SignatureOnLeaveRequestSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class LeaveRequestSimpleSerializer(serializers.ModelSerializer):
    user = ProfileSimpleSerializer(read_only=True)
    approved_by = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ProfileSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    user = UserSerializer(read_only=True)
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

class SubContractorWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubContractorWorker
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SubContractorOnProjectSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    class Meta:
        model = SubContractorOnProject
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SubContractorSerializer(serializers.ModelSerializer):
    locations = LocationSerializer(read_only=True)
    workers = SubContractorWorkerSerializer(many=True, read_only=True)
    subcontractors_on_project = SubContractorOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = SubContractor
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SubContractorSimpleSerializer(serializers.ModelSerializer):
    locations = LocationSerializer(read_only=True)

    class Meta:
        model = SubContractor
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')