from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hr", "0012_user_termination_date_user_termination_reason")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="external_user_id",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
