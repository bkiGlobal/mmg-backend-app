from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import *

@receiver(post_migrate)
def create_default_expense_categories(sender, **kwargs):
    default_categories = ["Labor", "Equipment", "Miscellaneous", "Travel", "Subcontractor", "Overhead"]
    for name in default_categories:
        ExpenseCategory.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_income_categories(sender, **kwargs):
    default_categories = ["Down Payment", "Progress Payment", "Final Payment"]
    for name in default_categories:
        IncomeCategory.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_document_type(sender, **kwargs):
    default_types = ['Project Proposal', 'Feasibility Study', 'Design Blueprint', 'Contract Agreement', 'Subcontract Agreement', 
                     'Purchase Order', 'Permit Application', 'Insurance Document', 'Daily Progress Report', 'Weekly Progress Report', 
                     'Monthly Progress Report', 'Inspection Report', 'Meeting Minutes', 'Payment Request', 'Invoice', 'Budget Plan', 
                     'Material Delivery Order', 'Usage Report', 'Safety Plan', 'Accident Report', 'Handover Certificate', 'Warranty Document']
    for name in default_types:
        DocumentType.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_work_types(sender, **kwargs):
    default_types = ["Foundation", "Structure", "Finishing", "Architecture", "MEP", "Other"]
    for name in default_types:
        WorkType.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_material_categories(sender, **kwargs):
    default_categories = ["Structural", "Finishing", "Electrical", "Plumbing", "Hardware", "Chemical", "Interior", "Exterior"]
    for name in default_categories:
        MaterialCategory.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_tool_categories(sender, **kwargs):
    default_categories = ["Hand Tool", "Power Tool", "Measuring", "Safety", "Heavy Equipment", "Cutting", "Lifting", "Demolition"]
    for name in default_categories:
        ToolCategory.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_unit_types(sender, **kwargs):
    default_types = ["Kilogram", "Gram", "Ton", "Pound", "Cubic Meter", "Litre", "Millilitre", "Gallon", "Cubic Feet", "Meter", 
                          "Centimeter", "Millimeter", "Inch", "Foot", "Square Meter", "Square Feet", "Unit", "Piece", "Set", "Box", 
                          "Roll", "Pack", "Sheet", "Bag", "Sack", "Drum", "Bundle", "Pallet", "Tube", "Bottle", "Can", "Carton", 
                          "Tray", "Roller", "Month", "Lump Sum"]
    for name in default_types:
        UnitType.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_finance_types(sender, **kwargs):
    default_categories = ["Capital", "Asset", "Operational", "Loan", "Entertaiment", "Equipment", "Transport", "Subcontractor", 'Salary', 'Income', 'Tax', 'Insurance']
    for name in default_categories:
        FinanceType.objects.get_or_create(name=name)

@receiver(post_migrate)
def create_default_payment_via(sender, **kwargs):
    default_categories = ["Cash", "Transfer"]
    for name in default_categories:
        PaymentVia.objects.get_or_create(name=name)