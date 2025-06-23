from django.contrib.gis.db import models as gis_models
from django.contrib import admin
from .models import *
import mapwidgets

admin.site.site_url = 'https://mmg-construction.com/'  

@admin.register(Location)
class LocationsModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)
    readonly_fields = ('latitude', 'longitude')
    
    formfield_overrides = {
        gis_models.PointField: {
            'widget': mapwidgets.GoogleMapPointFieldWidget,
        },
    }
    # gis_widget_kwargs = {
    #     'attrs': {
    #         'default_lat': -8.670458,  # ganti dengan latitude yang Anda inginkan
    #         'default_lon': 115.212631,  # ganti dengan longitude yang Anda inginkan
    #         'default_zoom': 12,         # ganti dengan level zoom yang diinginkan
    #     }
    # }

@admin.register(ExpenseCategory)
class ExpenseCategoryModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(IncomeCategory)
class IncomeCategoryModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(DocumentType)
class DocumentTypeModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(WorkType)
class WorkTypeModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(MaterialCategory)
class MaterialCategoryModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ToolCategory)
class ToolCategoryModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(UnitType)
class UnitTypeModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Brand)
class BrandModelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)