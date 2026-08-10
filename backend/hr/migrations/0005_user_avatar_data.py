from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hr", "0004_notification")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar_data",
            field=models.TextField(blank=True),
        ),
    ]
