from django.db import migrations
from django.utils.text import slugify


def populate_categories(apps, schema_editor):
    Category = apps.get_model('courses', 'Category')

    # Category Data: (Name, Icon Name)
    # Icons use common names (e.g., FontAwesome/HeroIcons)
    categories = [
        # --- BUSINESS & LEADERSHIP ---
        ("Business & Administration", "briefcase"),
        ("Leadership & Management", "users"),
        ("Finance & Accounting", "calculator"),
        ("Marketing & Sales", "trending-up"),
        ("Project Management", "clipboard-check"),

        # --- TECHNOLOGY & DATA ---
        ("Information Technology", "terminal"),
        ("Software Engineering", "code"),
        ("Data Science & AI", "cpu"),
        ("Cybersecurity", "shield-lock"),
        ("Cloud Computing", "cloud"),

        # --- NATURAL SCIENCES & MATH ---
        ("Mathematics & Statistics", "variable"),
        ("Physical Sciences", "flask"),
        ("Life Sciences", "dna"),
        ("Environmental Science", "leaf"),

        # --- SOCIAL SCIENCES & HUMANITIES ---
        ("Social Sciences", "globe"),
        ("Journalism & Information", "news"),
        ("History & Philosophy", "book-open"),
        ("Law & Legal Studies", "gavel"),

        # --- EDUCATION ---
        ("Teacher Training", "chalkboard-teacher"),
        ("Educational Science", "graduation-cap"),

        # --- CREATIVE & ARTS ---
        ("Graphic Design & Illustration", "palette"),
        ("Photography & Video", "camera"),
        ("Music & Audio Production", "music"),
        ("Architecture & Construction", "home"),

        # --- HEALTH & WELLBEING ---
        ("Health & Medicine", "heart-pulse"),
        ("Personal Development", "user-check"),
        ("Fitness & Sports", "activity"),

        # --- ENGINEERING & TRADES ---
        ("Mechanical Engineering", "settings"),
        ("Electrical Engineering", "zap"),
        ("Manufacturing & Trades", "hammer"),

        # --- GENERAL & LIFESTYLE ---
        ("Languages", "languages"),
        ("Office Productivity", "file-spreadsheet"),
    ]

    for name, icon in categories:
        # Generate the unique slug string dynamically (e.g. "data-science-ai")
        category_slug = slugify(name)

        # Look up or create based strictly on the unique identifier field
        Category.objects.get_or_create(
            slug=category_slug,
            defaults={
                'name': name,
                'icon': icon
            }
        )


def remove_categories(apps, schema_editor):
    Category = apps.get_model('courses', 'Category')
    Category.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0001_initial'),  # Ensure this matches your first migration
    ]
    operations = [
        migrations.RunPython(populate_categories, remove_categories),
    ]