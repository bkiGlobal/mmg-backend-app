from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, FloatWidget

from finance.models import *

class BillOfQuantityItemDetailResource(resources.ModelResource):
    """
    Resource ini digunakan untuk import baris detail. 
    Jika parent Item‐nya belum ada, maka dibuat; 
    jika parent SubItem belum ada, maka juga dibuat.
    """

    # Kolom kunci untuk menghubungkan ke parent BOQ (menggunakan ID Project atau ID BOQ)
    # Misalnya kita ingin men‐link ke BOQ tertentu lewat `bill_of_quantity_id`.
    bill_of_quantity = fields.Field(
        column_name='BOQ_ID',  # ganti sesuai kolom di Excel; atau bisa hanya gunakan --project secara global
        attribute='bill_of_quantity',
        widget=ForeignKeyWidget(BillOfQuantity, 'id'),
    )

    # Kolom ‘NO’ di sheet Excel—untuk memeriksa apakah row ini detail (numeric) atau bukan
    no = fields.Field(column_name='NO', attribute='item_number', widget=FloatWidget())

    # Deskripsi detail
    description = fields.Field(column_name='DESCRIPTION', attribute='description')

    # Quantity, Unit Price, Work Weight
    quantity   = fields.Field(column_name='QUANTITY', attribute='quantity', widget=FloatWidget())
    unit_price = fields.Field(column_name='UNIT_PRICE', attribute='unit_price', widget=FloatWidget())
    work_weight = fields.Field(column_name='WORK_WEIGHT', attribute='work_weight', widget=FloatWidget())

    # Kolom untuk parent item & subitem
    parent_item_code   = fields.Field(column_name='PARENT_ITEM', attribute='-', widget=FloatWidget())
    parent_subitem_code = fields.Field(column_name='PARENT_SUBITEM', attribute='-', widget=ForeignKeyWidget(BillOfQuantitySubItem, 'item_order'))

    # Kita set total_price di save() method model, jadi tidak perlu import kolom TOTAL_PRICE

    class Meta:
        model = BillOfQuantityItemDetail
        import_id_fields = ('id',)  # atau Anda bisa gunakan kombinasi (bill_of_quantity, item_number, …)
        fields = (
            'bill_of_quantity',
            'no',
            'description',
            'quantity',
            'unit_price',
            'work_weight',
            'parent_item_code',
            'parent_subitem_code',
        )
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        """
        Method ini dipanggil sebelum setiap baris di‐import. 
        Kita cek apakah row itu benar detail (numeric NO), lalu buat parent item & subitem.
        """

        no_val = row.get('NO')
        pid   = row.get('BOQ_ID')
        # Jika kolom NO bukan angka, skip (bukan detail)
        try:
            no_float = float(no_val)
        except (TypeError, ValueError):
            raise resources.fields.SkipRow(f"Baris '{no_val}' bukan baris detail, dilewati.")

        # Pastikan kita punya objek BOQ-nya
        try:
            boq = BillOfQuantity.objects.get(id=pid)
        except BillOfQuantity.DoesNotExist:
            raise resources.fields.SkipRow(f"BOQ dengan ID {pid} tidak ditemukan.")

        # 1) Buat atau ambil parent Item (BillOfQuantityItem) jika belum ada
        parent_item_code = row.get('PARENT_ITEM')
        # Kita anggap parent_item_code pasti numeric + ".0" → konversi ke float/int
        try:
            parent_item_no = float(parent_item_code)
        except (TypeError, ValueError):
            raise resources.fields.SkipRow(f"Parent Item '{parent_item_code}' tidak valid.")

        item_obj, created = BillOfQuantityItem.objects.get_or_create(
            bill_of_quantity=boq,
            item_number=parent_item_no,
            defaults={'title': f"Item {parent_item_no}", 'notes': ''}
        )
        if created:
            self.skip_row = False  # memastikan baris detail tetap diproses
            self._log(f"Item baru dibuat: {item_obj} untuk BOQ {boq.id}")

        # 2) Buat atau ambil parent SubItem (BillOfQuantitySubItem) jika belum ada
        parent_subitem_code = row.get('PARENT_SUBITEM')
        try:
            subitem_obj, created_sub = BillOfQuantitySubItem.objects.get_or_create(
                bill_of_quantity_item=item_obj,
                item_order=str(int(float(parent_subitem_code))),
                defaults={'title': f"SubItem {parent_subitem_code}", 'notes': ''}
            )
            if created_sub:
                self._log(f"SubItem baru dibuat: {subitem_obj} untuk Item {item_obj.id}")
        except (TypeError, ValueError):
            # Jika parent_subitem_code tidak ada (NaN atau string), buat satu default
            subitem_obj = BillOfQuantitySubItem.objects.get_or_create(
                bill_of_quantity_item=item_obj,
                item_order="default",
                defaults={'title': f"Default SubItem for Item {item_obj.id}", 'notes': ''}
            )[0]
            self._log(f"SubItem default dibuat: {subitem_obj} untuk Item {item_obj.id}")

        # Simpan sementara objek parent_item dan parent_subitem di `row` agar nanti di import_row kita bisa akses
        row['__parent_item_obj']    = item_obj
        row['__parent_subitem_obj'] = subitem_obj

    def import_row(self, row, instance_loader, **kwargs):
        """
        Override import_row supaya kita teruskan `parent_subitem_obj` 
        sebagai `bill_of_quantity_subitem` saat membuat detail.
        """
        # Jika kita skip baris ini (bukan detail), kembalikan super().import_row
        if getattr(self, 'skip_row', False):
            self.skip_row = False  # reset flag
            return super().import_row(row, instance_loader, **kwargs)

        # Ambil parent subitem yang sudah kita set di before_import_row
        subitem_obj = row.get('__parent_subitem_obj')
        if not subitem_obj:
            raise resources.fields.SkipRow("Parent SubItem tidak tersedia.")

        # Buat atau update BillOfQuantityItemDetail
        # Kita assign `bill_of_quantity_subitem=subitem_obj`
        data_for_detail = {
            'bill_of_quantity_subitem': subitem_obj,
            'item_number': int(float(row.get('NO'))),
            'description': row.get('DESCRIPTION'),
            'quantity': float(row.get('QUANTITY') or 0),
            'unit_price': float(row.get('UNIT_PRICE') or 0),
            # total_price akan dihitung oleh model.save()
            'work_weight': float(row.get('WORK_WEIGHT') or 0),
            'notes': '',
        }

        # Jika ada instance lama (bergantung import_id_fields), ubah, jika tidak, buat baru
        return super().import_row(row, instance_loader, **kwargs, **data_for_detail)

    def after_save_instance(self, instance, using_transactions, dry_run):
        """
        Setelah detail tersimpan, kita hitung ulang total di BOQ header.
        """
        boq = instance.bill_of_quantity_subitem.bill_of_quantity_item.bill_of_quantity
        boq.recalc_total()