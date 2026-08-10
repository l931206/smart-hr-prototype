from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("hr", "0006_latenotice")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="manager",
            field=models.ForeignKey(blank=True, limit_choices_to={"role": "manager"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="direct_reports", to="hr.user"),
        ),
    ]
