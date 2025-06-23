from datetime import timezone
import os
import uuid
from django.conf import settings
from django.db import models
from core.models import *
from project.models import Project
from team.models import Profile
from djmoney.models.fields import MoneyField

# class UnitType(models.TextChoices):
#     KG = "kg", "Kilogram"
#     G = "g", "Gram"
#     TON = "ton", "Ton"
#     LB = "lb", "Pound"
#     M3 = "m3", "Cubic Meter"
#     L = "l", "Litre"
#     ML = "ml", "Millilitre"
#     GAL = "gal", "Gallon"
#     FT3 = "ft3", "Cubic Feet"
#     M = "m", "Meter"
#     CM = "cm", "Centimeter"
#     MM = "mm", "Millimeter"
#     INCH = "in", "Inch"
#     FT = "ft", "Foot"
#     M2 = "m2", "Square Meter"
#     FT2 = "ft2", "Square Feet"
#     UNIT = "unit", "Unit"
#     PCS = "pcs", "Piece"
#     SET = "set", "Set"
#     BOX = "box", "Box"
#     ROLL = "roll", "Roll"
#     PACK = "pack", "Pack"
#     SHEET = "sheet", "Sheet"
#     BAG = "bag", "Bag"
#     SACK = "sack", "Sack"
#     DRUM = "drum", "Drum"
#     BUNDLE = "bundle", "Bundle"
#     PALLET = "pallet", "Pallet"
#     TUBE = "tube", "Tube"
#     BOTTLE = "bottle", "Bottle"
#     CAN = "can", "Can"
#     CARTON = "carton", "Carton"
#     TRAY = "tray", "Tray"
#     ROLLER = "roller", "Roller"
#     MONTH = "month", "Month"
#     LUMP_SUM = "ls", "Lump Sum"

# class MaterialCategory(models.TextChoices):
#     STRUCTURAL = "structural", "Structural"
#     FINISHING = "finishing", "Finishing"
#     ELECTRICAL = "electrical", "Electrical"
#     PLUMBING = "plumbing", "Plumbing"
#     HARDWARE = "hardware", "Hardware"
#     CHEMICAL = "chemical", "Chemical"
#     INTERIOR = "interior", "Interior"
#     EXTERIOR = "exterior", "Exterior"
#     OTHER = "other", "Other"

# class ToolCategory(models.TextChoices):
#     HAND_TOOL = "hand_tool", "Hand Tool"
#     POWER_TOOL = "power_tool", "Power Tool"
#     MEASURING = "measuring", "Measuring"
#     SAFETY = "safety", "Safety"
#     HEAVY_EQUIPMENT = "heavy_equipment", "Heavy Equipment"
#     CUTTING = "cutting", "Cutting"
#     LIFTING = "lifting", "Lifting"
#     DEMOLITION = "demolition", "Demolition"
#     OTHER = "other", "Other"

def upload_tools(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'TLS_{timestamp_now}.jpeg'
    return os.path.join('tool', filename)

def upload_materials(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'MTR_{timestamp_now}.jpeg'
    return os.path.join('material', filename)

def upload_materials_project(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'MDT_{timestamp_now}.jpeg'
    return os.path.join('material_project', filename)

class Material(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True)
    unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    photo = models.ImageField(upload_to=upload_materials, null=True, blank=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=128)
    standart_price = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    descriptions = models.TextField()

    def __str__(self) -> str:
        return self.name
    
class MaterialOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_material')
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, related_name='material_project', null=True, blank=True)
    photo = models.ImageField(upload_to=upload_materials_project, null=True, blank=True)
    stock = models.FloatField()
    quantity_used = models.FloatField()
    notes = models.TextField()
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField()

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.material.name}'

class Tool(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(ToolCategory, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to=upload_tools, null=True, blank=True)
    serial_number = models.CharField(max_length=255)
    conditions = models.TextField()
    amount = models.IntegerField()
    available = models.IntegerField()

    def __str__(self) -> str:
        return self.name

class ToolOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_tools')
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='tools_project')
    amount = models.IntegerField()
    assigned_date = models.DateField()
    returned_date = models.DateField()

    def __str__(self) -> str:
        return f'{self.tool.name} on {self.project.project_name}'