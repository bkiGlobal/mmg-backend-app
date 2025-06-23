from import_export import resources, fields, widgets
from import_export.widgets import FloatWidget, ForeignKeyWidget
from finance.models import *

# class BillOfQuantityItemDetailResource(resources.ModelResource):
#     # 1) Kolom untuk cari BOQ yang sudah ada (harus disiapkan di Excel)
#     boq = fields.Field(
#         column_name='BOQ_ID',
#         attribute='bill_of_quantity',
#         widget=widgets.ForeignKeyWidget(BillOfQuantity, 'id'),
#     )

#     # 2) Detail fields
#     no          = fields.Field(column_name='NO', attribute='item_number', widget=FloatWidget())
#     description = fields.Field(column_name='DESCRIPTION', attribute='description')
#     quantity    = fields.Field(column_name='QUANTITY', attribute='quantity', widget=FloatWidget())
#     unit_price  = fields.Field(column_name='UNIT_PRICE', attribute='unit_price', widget=FloatWidget())
#     work_weight = fields.Field(column_name='WORK_WEIGHT', attribute='work_weight', widget=FloatWidget())

#     # 3) Untuk membangun hierarchy parent → child
#     parent_item_code    = fields.Field(column_name='PARENT_ITEM', attribute=None)
#     parent_subitem_code = fields.Field(column_name='PARENT_SUBITEM', attribute=None)

#     class Meta:
#         model = BillOfQuantityItemDetail
#         # import_id_fields = ('id',)   # atau kombinasi lain jika Anda punya ID di Excel
#         fields = (
#             'boq',
#             'no',
#             'description',
#             'quantity',
#             'unit_price',
#             'work_weight',
#             'parent_item_code',
#             'parent_subitem_code',
#         )
#         skip_unchanged = True
#         report_skipped = True

#     def skip_row(self, instance, original):
#         """
#         Abaikan baris yang bukan detail (misalnya baris item '2.0' atau subitem 'A').
#         Kita anggap baris detail memiliki kolom NO yang bisa di‐cast ke float
#         dan memiliki PARENT_ITEM (kode item induk).
#         """
#         no_val = original.get('NO')
#         parent_item = original.get('PARENT_ITEM')
#         try:
#             # kalau NO bukan angka, akan error
#             float(no_val)
#             # juga wajib ada parent_item
#             if parent_item in (None, '', 'nan'):
#                 return True
#             return False
#         except Exception:
#             return True

#     def before_import_row(self, row, **kwargs):
#         """
#         Pastikan parent BillOfQuantityItem & BillOfQuantitySubItem sudah ada atau dibuat.
#         (untuk baris yang lolos skip_row).
#         """
#         # Pasti baris detail di sini
#         boq_id = row['BOQ_ID']
#         parent_item_code = row['PARENT_ITEM']
#         parent_sub_code  = row['PARENT_SUBITEM']

#         # Ambil BOQ
#         boq = BillOfQuantity.objects.get(id=boq_id)

#         # 1) Parent Item (create if not exists)
#         item_no = float(parent_item_code)
#         item_obj, created = BillOfQuantityItem.objects.get_or_create(
#             bill_of_quantity=boq,
#             item_number=item_no,
#             defaults={'title': f"Item {item_no}", 'notes': ''}
#         )

#         # 2) Parent SubItem (create jika belum)
#         try:
#             sub_code = str(parent_sub_code).strip()
#             sub_obj, created_sub = BillOfQuantitySubItem.objects.get_or_create(
#                 bill_of_quantity_item=item_obj,
#                 item_order=sub_code,
#                 defaults={'title': f"SubItem {sub_code}", 'notes': ''}
#             )
#         except Exception:
#             # fallback: subitem default
#             sub_obj, created_sub = BillOfQuantitySubItem.objects.get_or_create(
#                 bill_of_quantity_item=item_obj,
#                 item_order='default',
#                 defaults={'title': 'Default SubItem', 'notes': ''}
#             )

#         # Simpan parent‐parent ini untuk nanti kita gunakan di import_obj()
#         row['_boq_item']    = item_obj
#         row['_boq_subitem'] = sub_obj

#     def import_obj(self, row, instance_loader, **kwargs):
#         """
#         Buat atau update BillOfQuantityItemDetail menggunakan parent yang disimpan
#         di row['_boq_subitem'].
#         """
#         # Siapkan data baru
#         subitem = row.pop('_boq_subitem')
#         detail_data = {
#             'bill_of_quantity_subitem': subitem,
#             'item_number': int(float(row['NO'])),
#             'description': row['DESCRIPTION'],
#             'quantity': float(row['QUANTITY'] or 0),
#             'unit_price': float(row['UNIT_PRICE'] or 0),
#             'work_weight': float(row['WORK_WEIGHT'] or 0),
#             'notes': '',
#         }
#         # Gunakan instance_loader untuk cek apakah instance sudah ada (berdasarkan import_id_fields)
#         # Kalau sudah ada → update, kalau tidak → create
#         return super().import_obj({**row, **detail_data}, instance_loader, **kwargs)

#     def after_save_instance(self, instance, using_transactions, dry_run):
#         """
#         Setelah setiap detail tersimpan, update total di BOQ header.
#         """
#         boq = instance.bill_of_quantity_subitem.bill_of_quantity_item.bill_of_quantity
#         boq.recalc_total()

class IncomeDetailInlineResource(resources.ModelResource):
    class Meta:
        model = IncomeDetail
        fields = (
            'income',
            'name', 'quantity', 'unit_price', 'unit', 
            'subtotal', 'discount', 'discount_type', 
            'discount_amount', 'total', 'notes'
        )
        import_id_fields = ('id',)

class IncomeResource(resources.ModelResource):
    class Meta:
        model = Income
        skip_unchanged = True
        report_skipped = True
        fields = ('id','project','received_from','total','category','payment_date','notes')

class IncomeDetailResource(resources.ModelResource):
    class Meta:
        model = IncomeDetail
        skip_unchanged = True
        report_skipped = True
        fields = ('id','income','name','quantity','unit_price','unit','subtotal','discount','discount_type','discount_amount','total','notes')

class ExpenseResource(resources.ModelResource):
    class Meta:
        model = ExpenseOnProject
        skip_unchanged = True
        report_skipped = True
        # import_id_fields   = ('branch', 'date', 'due_date', 'description', 'total_amount', 'timestamp')
        fields = ('id', 'project', 'date', 'total', 'notes', 'payment_proof')

class ExpenseDetailResource(resources.ModelResource):
    class Meta:
        model = ExpenseDetail
        skip_unchanged = True
        report_skipped = True
        fields = (
            'id', 'expense', 'category', 'name', 'quantity', 
            'unit_price', 'unit', 'subtotal', 'discount', 
            'discount_type', 'discount_amount', 'total', 'notes'
        )

class ExpenseForMaterialResource(resources.ModelResource):
    class Meta:
        model = ExpenseForMaterial
        skip_unchanged = True
        report_skipped = True
        fields = (
            'id', 'expense', 'material', 'category', 
            'quantity', 'unit_price', 'unit', 
            'subtotal', 'discount', 'discount_type', 
            'discount_amount', 'total'
        )