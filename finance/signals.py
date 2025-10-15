# from django.db.models.signals import pre_delete, post_save
# from django.dispatch import receiver
# from .models import *

# @receiver(pre_delete, sender=BillOfQuantity)
# def delete_on_boq(sender, instance, **kwargs):
#     list_versions = instance.boq_versions.all()
#     list_signatures = instance.boq_signatures.all()
#     print(f"Deleting BillOfQuantity: {instance.id}, versions: {list_versions.count()}, signatures: {list_signatures.count()}")
#     list_versions.delete()
#     list_signatures.delete()

# @receiver(post_save, sender=BillOfQuantity)
# def update_work_weight_on_boq_save(sender, instance: BillOfQuantity, created, **kwargs):
#     """
#     Setelah BillOfQuantity disimpan, hitung work_weight untuk semua detailnya:
#         work_weight = detail.total_price / boq.total
#     Hanya lakukan jika total tidak None dan > 0.
#     """
#     # Abaikan jika total None atau 0
#     if not instance.total:
#         return

#     # Ambil semua detail yang berkaitan dengan BOQ ini
#     details_qs = BillOfQuantityItemDetail.objects.filter(
#         bill_of_quantity_subitem__bill_of_quantity_item__bill_of_quantity=instance
#     )

#     # Update work_weight setiap detail
#     details = []
#     for d in details_qs:
#         # calculate
#         d.work_weight = d.total_price / instance.total
#         details.append(d)

#     # Bulk update untuk efisiensi
#     if details:
#         BillOfQuantityItemDetail.objects.bulk_update(details, ['work_weight'])