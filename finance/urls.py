from django.urls import path
from .views import *

urlpatterns = [
    path('boq/', BillOfQuantityAPIView.as_view(), name='boq_list'),
    path('boq/<str:pk>/', BillOfQuantityAPIView.as_view(), name='boq_detail'),
    path('boq-version/', BillOfQuantityVersionAPIView.as_view(), name='boq_version_list'),
    path('boq-version/<str:pk>/', BillOfQuantityVersionAPIView.as_view(), name='boq_version_detail'),
    path('boq-signature/', SignatureOnBillOfQuantityAPIView.as_view(), name='boq_signature_list'),
    path('boq-signature/<str:pk>/', SignatureOnBillOfQuantityAPIView.as_view(), name='boq_signature_detail'),
    path('payment-request/', PaymentRequestAPIView.as_view(), name='payment_request_list'),
    path('payment-request/<str:pk>/', PaymentRequestAPIView.as_view(), name='payment_request_detail'),
    path('payment-request-version/', PaymentRequestVersionAPIView.as_view(), name='payment_request_version_list'),
    path('payment-request-version/<str:pk>/', PaymentRequestVersionAPIView.as_view(), name='payment_request_version_detail'),
    path('payment-request-signature/', SignatureOnPaymentRequestAPIView.as_view(), name='payment_request_signature_list'),
    path('payment-request-signature/<str:pk>/', SignatureOnPaymentRequestAPIView.as_view(), name='payment_request_signature_detail'),
    path('expense/', ExpenseOnProjectAPIView.as_view(), name='expense_list'),
    path('expense/<str:pk>/', ExpenseOnProjectAPIView.as_view(), name='expense_detail'),
    path('expense-detail/', ExpenseDetailAPIView.as_view(), name='expense_detail_list'),
    path('expense-detail/<str:pk>/', ExpenseDetailAPIView.as_view(), name='expense_detail_detail'),
    path('expense-material/', ExpenseForMaterialAPIView.as_view(), name='expense_material_list'),
    path('expense-material/<str:pk>/', ExpenseForMaterialAPIView.as_view(), name='expense_material_detail'),
    path('finance/', FinanceDataAPIView.as_view(), name='finance_list'),
    path('finance/<str:pk>/', FinanceDataAPIView.as_view(), name='finance_detail'),
    path('petty-cash/', PettyCashAPIView.as_view(), name='petty_cash_list'),
    path('petty-cash/<str:pk>/', PettyCashAPIView.as_view(), name='petty_cash_detail'),
]