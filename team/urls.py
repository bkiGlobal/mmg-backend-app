from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from core.views import CustomTokenRefreshView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('change_password/', ChangePasswordAPIView.as_view(), name='change_password'),
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('profile/', ProfileModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='profile_list'),
    path('profile/<str:pk>/', ProfileModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='profile_detail'),
    path('team/', TeamModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='team_list'),
    path('team/<str:pk>/', TeamModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='team_detail'),
    path('team-member/', TeamMemberModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='team_member_list'),
    path('team-member/<str:pk>/', TeamMemberModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='team_member_detail'),
    path('signature/', SignatureModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='signature_list'),
    path('signature/<str:pk>/', SignatureModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='signature_detail'),
    path('initial/', InitialModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='initial_list'),
    path('initial/<str:pk>/', InitialModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='initial_detail'),
    path('notification/', NotificationModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='notification_list'),
    path('notification/<str:pk>/', NotificationModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='notification_detail'),
    path('sub-contractor/', SubContractorModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='subcontractor_list'),
    path('sub-contractor/<str:pk>/', SubContractorModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='subcontractor_detail'),
    path('sub-contractor-worker/', SubContractorWorkerModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='subcontractor_worker_list'),
    path('sub-contractor-worker/<str:pk>/', SubContractorWorkerModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='subcontractor_worker_detail'),
    path('sub-contractor-on-project/', SubContractorOnProjectModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='subcontractor_on_project_list'),
    path('sub-contractor-on-project/<str:pk>/', SubContractorOnProjectModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='subcontractor_on_project_detail'),
    path('attendance/', AttendanceModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='attendance_list'),
    path('attendance/<str:pk>/', AttendanceModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='attendance_detail'),
    path('checkin/', CheckInView.as_view(), name='checkin'), #pass employee, branch, langitude, latitude, and photo
    path('checkout/', CheckOutView.as_view(), name='checkout'), #pass employee, branch, langitude, and latitude
    path('leave-request/', LeaveRequestModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='leave_request_list'),
    path('leave-request/<str:pk>/', LeaveRequestModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='leave_request_detail'),
    path('signature-on-leave-request/', SignatureOnLeaveRequestModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='signature_on_leave_request_list'),
    path('signature-on-leave-request/<str:pk>/', SignatureOnLeaveRequestModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='signature_on_leave_request_detail'),
    path('announcement/', AnnouncementModelViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='announcement_list'),
    path('announcement/<str:pk>/', AnnouncementModelViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    }), name='sannouncement_detail'),
]
