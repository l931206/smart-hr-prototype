from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("hr", "0002_leaverequest")]

    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField()),
                ("category", models.CharField(choices=[("company", "公司公告"), ("system", "系統公告"), ("hr", "人事公告"), ("admin", "行政公告")], default="company", max_length=20)),
                ("is_published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="announcements", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-published_at", "-created_at"]},
        ),
    ]
