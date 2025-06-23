# from django.db.models.signals import post_delete, post_save
# from django.dispatch import receiver
# from .models import BillOfQuantityItemDetail, BillOfQuantity

# @receiver(post_delete, sender=BillOfQuantityItemDetail)
# def update_total_on_delete(sender, instance, **kwargs):
#     instance.bill_of_quantity_subitem.bill_of_quantity_item.bill_of_quantity.recalc_total()

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