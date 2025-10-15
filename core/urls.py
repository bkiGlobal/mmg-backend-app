from django.urls import path
from .views import *

urlpatterns = [
    path('location/', LocationAPIView.as_view(), name='location_list'),
    path('location/<str:pk>/', LocationAPIView.as_view(), name='location_detail'),
    path('expense-category/', ExpenseCategoryAPIView.as_view(), name='expense_category_list'),
    path('expense-category/<str:pk>/', ExpenseCategoryAPIView.as_view(), name='expense_category_detail'),
    path('income-category/', IncomeCategoryAPIView.as_view(), name='income_category_list'),
    path('income-category/<str:pk>/', IncomeCategoryAPIView.as_view(), name='income_category_detail'),
    path('document-type/', DocumentTypeAPIView.as_view(), name='document_type_list'),
    path('document-type/<str:pk>/', DocumentTypeAPIView.as_view(), name='document_type_detail'),
    path('work-type/', WorkTypeAPIView.as_view(), name='work_type_list'),
    path('work-type/<str:pk>/', WorkTypeAPIView.as_view(), name='work_type_detail'),
    path('material-category/', MaterialCategoryAPIView.as_view(), name='material_category_list'),
    path('material-category/<str:pk>/', MaterialCategoryAPIView.as_view(), name='material_category_detail'),
    path('tool-category/', ToolCategoryAPIView.as_view(), name='tool_category_list'),
    path('tool-category/<str:pk>/', ToolCategoryAPIView.as_view(), name='tool_category_detail'),
    path('unit-type/', UnitTypeAPIView.as_view(), name='unit_type_list'),
    path('unit-type/<str:pk>/', UnitTypeAPIView.as_view(), name='unit_type_detail'),
    path('brand/', BrandAPIView.as_view(), name='brand_list'),
    path('brand/<str:pk>/', BrandAPIView.as_view(), name='brand_detail'),
    path('finance-type/', FinanceTypeAPIView.as_view(), name='finance_type_list'),
    path('finance-type/<str:pk>/', FinanceTypeAPIView.as_view(), name='finance_type_detail'),
    path('payment-via/', PaymentViaAPIView.as_view(), name='payment_via_list'),
    path('payment-via/<str:pk>/', PaymentViaAPIView.as_view(), name='payment_via_detail'),
]