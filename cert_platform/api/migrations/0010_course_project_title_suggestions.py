from django.db import migrations, models


def seed_project_title_suggestions(apps, schema_editor):
    Course = apps.get_model("api", "Course")
    for course in Course.objects.all():
        # Provide generic but relevant templates using the course title
        title = course.title or "Capstone"
        suggestions = [
            f"{title}: KPI Dashboard & Insights",
            f"{title}: Predictive Analytics Pipeline",
            f"{title}: End-to-End Automation Project",
        ]
        course.project_title_suggestions = suggestions
        course.save(update_fields=["project_title_suggestions"])


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0009_planconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="project_title_suggestions",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(seed_project_title_suggestions, migrations.RunPython.noop),
    ]

