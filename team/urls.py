from django.urls import path
from .views import *

urlpatterns = [
    path('profile/', ProfileAPIView.as_view(), name='profile_list'),
    path('profile/<str:pk>/', ProfileAPIView.as_view(), name='profile_detail'),
    path('team/', TeamAPIView.as_view(), name='team_list'),
    path('team/<str:pk>/', TeamAPIView.as_view(), name='team_detail'),
    path('team-member/', TeamMemberAPIView.as_view(), name='team_member_list'),
    path('team-member/<str:pk>/', TeamMemberAPIView.as_view(), name='team_member_detail'),
    path('signature/', SignatureAPIView.as_view(), name='signature_list'),
    path('signature/<str:pk>/', SignatureAPIView.as_view(), name='signature_detail'),
    path('initial/', InitialAPIView.as_view(), name='initial_list'),
    path('initial/<str:pk>/', InitialAPIView.as_view(), name='initial_detail'),
    path('notification/', NotificationAPIView.as_view(), name='notification_list'),
    path('notification/<str:pk>/', NotificationAPIView.as_view(), name='notification_detail'),
    path('sub-contractor/', SubContractorAPIView.as_view(), name='subcontractor_list'),
    path('sub-contractor/<str:pk>/', SubContractorAPIView.as_view(), name='subcontractor_detail'),
    path('sub-contractor-worker/', SubContractorWorkerAPIView.as_view(), name='subcontractor_worker_list'),
    path('sub-contractor-worker/<str:pk>/', SubContractorWorkerAPIView.as_view(), name='subcontractor_worker_detail'),
    path('sub-contractor-on-project/', SubContractorOnProjectAPIView.as_view(), name='subcontractor_on_project_list'),
    path('sub-contractor-on-project/<str:pk>/', SubContractorOnProjectAPIView.as_view(), name='subcontractor_on_project_detail'),
    path('attendance/', AttendanceAPIView.as_view(), name='attendance_list'),
    path('attendance/<str:pk>/', AttendanceAPIView.as_view(), name='attendance_detail'),
    path('leave-request/', LeaveRequestAPIView.as_view(), name='leave_request_list'),
    path('leave-request/<str:pk>/', LeaveRequestAPIView.as_view(), name='leave_request_detail'),
    path('signature-on-leave-request/', SignatureOnLeaveRequestAPIView.as_view(), name='signature_on_leave_request_list'),
    path('signature-on-leave-request/<str:pk>/', SignatureOnLeaveRequestAPIView.as_view(), name='signature_on_leave_request_detail'),
]
