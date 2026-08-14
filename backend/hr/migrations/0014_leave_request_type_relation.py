from django.db import migrations, models
import django.db.models.deletion


def connect_leave_types(apps, schema_editor):
    LeaveRequest = apps.get_model("hr", "LeaveRequest")
    LeaveType = apps.get_model("hr", "LeaveType")
    for request in LeaveRequest.objects.all():
        name = request.leave_type_legacy.strip() or "未分類假別"
        leave_type = LeaveType.objects.filter(name=name).first()
        if not leave_type:
            leave_type = LeaveType.objects.create(
                code=f"LEGACY-{request.pk}",
                name=name,
                deduct_quota=False,
                is_active=False,
            )
        request.leave_type = leave_type
        request.save(update_fields=["leave_type"])


class Migration(migrations.Migration):
    dependencies = [("hr", "0013_user_external_user_id")]

    operations = [
        migrations.RenameField(
            model_name="leaverequest",
            old_name="leave_type",
            new_name="leave_type_legacy",
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="leave_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="requests",
                to="hr.leavetype",
            ),
        ),
        migrations.RunPython(connect_leave_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="leaverequest",
            name="leave_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="requests",
                to="hr.leavetype",
            ),
        ),
        migrations.RemoveField(model_name="leaverequest", name="leave_type_legacy"),
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[("pending", "待審核"), ("approved", "已核准"), ("rejected", "已退回"), ("withdrawn", "已撤回")],
                default="pending",
                max_length=20,
            ),
        ),
    ]
