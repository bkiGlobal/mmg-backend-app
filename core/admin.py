from django.contrib.gis.db import models
from django.contrib import admin
from .models import Location
import mapwidgets

admin.site.site_url = 'https://mmg-construction.com/'  

@admin.register(Location)
class LocationsModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)
    readonly_fields = ('latitude', 'longitude')
    
    formfield_overrides = {
        models.PointField: {
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