from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import BillOfQuantityItemDetail

@receiver(post_delete, sender=BillOfQuantityItemDetail)
def update_total_on_delete(sender, instance, **kwargs):
    instance.bill_of_quantity_item.bill_of_quantity.recalc_total()