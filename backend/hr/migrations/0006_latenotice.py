from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("hr", "0005_user_avatar_data")]

    operations = [
        migrations.CreateModel(
            name="LateNotice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("expected_arrival", models.TimeField()),
                ("reason_type", models.CharField(max_length=50)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("notified", "已通知主管"), ("arrived", "已到班")], default="notified", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="late_notices", to="hr.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
