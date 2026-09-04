from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Attendance,
    AttendanceStatus,
    AttendanceWorkMode,
    Holiday,
    LeaveRequest,
    LeaveStatus,
    NotificationCategory,
    Notifications,
    Profile,
    WorkPolicy,
)


@dataclass(frozen=True)
class AttendanceLocationValidation:
    current_point: Point
    expected_point: Point
    expected_location: object
    distance_meters: float
    radius_meters: int
    label: str


def notify_profiles(
    profiles,
    title,
    message,
    category=NotificationCategory.GENERAL,
    action_url='',
    dedupe_key='',
):
    """Kirim inbox notification dengan deduplikasi opsional."""
    created = []
    for profile in profiles:
        values = {
            'title': title,
            'message': message,
            'category': category,
            'action_url': action_url,
            'sent_at': timezone.now(),
            'is_read': False,
        }
        if dedupe_key:
            notification, was_created = Notifications.objects.get_or_create(
                user=profile,
                dedupe_key=dedupe_key,
                defaults=values,
            )
        else:
            notification = Notifications.objects.create(
                user=profile,
                dedupe_key='',
                **values,
            )
            was_created = True
        if was_created:
            created.append(notification)
    return created


def notify_users(users, **kwargs):
    profiles = Profile.objects.filter(user__in=users, is_active=True)
    return notify_profiles(profiles, **kwargs)


def get_effective_work_policy(profile):
    return (
        profile.work_policy
        or WorkPolicy.objects.filter(is_active=True).order_by('pk').first()
    )


def get_attendance_location(
    profile,
    work_policy=None,
    work_mode=AttendanceWorkMode.OFFICE,
):
    """
    Tentukan titik referensi absensi.

    Office memakai titik kantor dari work policy. WFH memakai alamat rumah
    yang telah disetujui pada profile dan hanya tersedia bila policy
    mengizinkannya. Fungsi ini tidak pernah menganggap titik referensi sebagai
    lokasi aktual user.
    """
    policy = work_policy or get_effective_work_policy(profile)
    if work_mode == AttendanceWorkMode.WFH:
        if policy is None or not policy.allow_wfh:
            raise ValidationError(
                'Work From Home tidak diizinkan oleh work policy Anda.'
            )
        location = profile.location
        missing_message = (
            'Alamat rumah pada profile belum dikonfigurasi untuk WFH.'
        )
    else:
        location = policy.office_location if policy else None
        missing_message = (
            'Lokasi kantor pada work policy belum dikonfigurasi.'
        )

    if location is None or location.address is None:
        raise ValidationError(missing_message)

    address = location.address
    point = Point(
        address.x,
        address.y,
        srid=address.srid or 4326,
    )
    return location, point


def calculate_distance_meters(point_a, point_b):
    """Hitung jarak Haversine dua GeoDjango Point dalam meter."""
    if point_a is None or point_b is None:
        raise ValidationError('Koordinat GPS tidak tersedia.')

    lat1 = radians(point_a.y)
    lon1 = radians(point_a.x)
    lat2 = radians(point_b.y)
    lon2 = radians(point_b.x)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return 6_371_000 * 2 * asin(sqrt(haversine))


def validate_attendance_location(
    profile,
    work_policy,
    work_mode,
    current_point,
):
    """Validasi GPS aktual terhadap titik dan radius mode kerja."""
    if current_point is None:
        raise ValidationError(
            'Lokasi GPS terkini wajib diaktifkan untuk absensi.'
        )
    if not isinstance(current_point, Point):
        raise ValidationError('Format lokasi GPS terkini tidak valid.')
    if current_point.srid is None:
        current_point.srid = 4326
    elif current_point.srid != 4326:
        current_point.transform(4326)

    policy = work_policy or get_effective_work_policy(profile)
    expected_location, expected_point = get_attendance_location(
        profile,
        policy,
        work_mode,
    )
    if work_mode == AttendanceWorkMode.WFH:
        radius = policy.wfh_geofence_radius_meters
        label = f'WFH · {expected_location.name}'
    else:
        radius = policy.geofence_radius_meters
        label = f'Office · {expected_location.name}'

    distance = calculate_distance_meters(current_point, expected_point)
    if distance > radius:
        raise ValidationError(
            (
                f'Lokasi Anda berjarak {distance:.0f} meter dari '
                f'{expected_location.name}. Batas untuk '
                f'{dict(AttendanceWorkMode.choices)[work_mode]} adalah '
                f'{radius} meter.'
            )
        )

    return AttendanceLocationValidation(
        current_point=current_point,
        expected_point=expected_point,
        expected_location=expected_location,
        distance_meters=distance,
        radius_meters=radius,
        label=label[:108],
    )


@transaction.atomic
def generate_daily_attendance(target_date):
    """Buat record leave/holiday/absent yang belum tercatat."""
    holiday = Holiday.objects.filter(date=target_date).first()
    created_count = 0

    profiles = Profile.objects.filter(
        is_active=True,
        user__is_active=True,
    ).select_related('work_policy')
    for profile in profiles.iterator(chunk_size=200):
        if Attendance.objects.filter(
            user=profile, date=target_date
        ).exists():
            continue

        policy = get_effective_work_policy(profile)
        workdays = policy.workdays if policy else [0, 1, 2, 3, 4]
        # Akhir pekan memang bukan hari kerja, jadi tidak perlu record apa pun
        # walaupun kebetulan bertepatan dengan hari libur nasional.
        if target_date.weekday() not in workdays:
            continue

        if holiday:
            attendance_status = AttendanceStatus.HOLYDAY
        elif LeaveRequest.objects.filter(
            user=profile,
            status=LeaveStatus.APPROVED,
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).exists():
            attendance_status = AttendanceStatus.LEAVE
        else:
            attendance_status = AttendanceStatus.ABSENT

        Attendance.objects.create(
            user=profile,
            date=target_date,
            status=attendance_status,
            work_policy=policy,
        )
        created_count += 1

        if attendance_status == AttendanceStatus.ABSENT:
            notify_profiles(
                [profile],
                title='Absensi belum tercatat',
                message=f'Tidak ada check-in pada {target_date:%d-%m-%Y}.',
                category=NotificationCategory.ATTENDANCE,
                dedupe_key=f'attendance-absent:{profile.pk}:{target_date}',
            )

    return created_count
