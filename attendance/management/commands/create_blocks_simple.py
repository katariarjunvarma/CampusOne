from django.core.management.base import BaseCommand
from attendance.models import Block


class Command(BaseCommand):
    help = "Create 36 campus blocks with names Block-1 to Block-36 in ascending order"

    def handle(self, *args, **options):
        blocks_data = [
            ("Block-1", "BLOCK-1"),
            ("Block-2", "BLOCK-2"),
            ("Block-3", "BLOCK-3"),
            ("Block-4", "BLOCK-4"),
            ("Block-5", "BLOCK-5"),
            ("Block-6", "BLOCK-6"),
            ("Block-7", "BLOCK-7"),
            ("Block-8", "BLOCK-8"),
            ("Block-9", "BLOCK-9"),
            ("Block-10", "BLOCK-10"),
            ("Block-11", "BLOCK-11"),
            ("Block-12", "BLOCK-12"),
            ("Block-13", "BLOCK-13"),
            ("Block-14", "BLOCK-14"),
            ("Block-15", "BLOCK-15"),
            ("Block-16", "BLOCK-16"),
            ("Block-17", "BLOCK-17"),
            ("Block-18", "BLOCK-18"),
            ("Block-19", "BLOCK-19"),
            ("Block-20", "BLOCK-20"),
            ("Block-21", "BLOCK-21"),
            ("Block-22", "BLOCK-22"),
            ("Block-23", "BLOCK-23"),
            ("Block-24", "BLOCK-24"),
            ("Block-25", "BLOCK-25"),
            ("Block-26", "BLOCK-26"),
            ("Block-27", "BLOCK-27"),
            ("Block-28", "BLOCK-28"),
            ("Block-29", "BLOCK-29"),
            ("Block-30", "BLOCK-30"),
            ("Block-31", "BLOCK-31"),
            ("Block-32", "BLOCK-32"),
            ("Block-33", "BLOCK-33"),
            ("Block-34", "BLOCK-34"),
            ("Block-35", "BLOCK-35"),
            ("Block-36", "BLOCK-36"),
        ]

        created = 0
        skipped = 0
        for code, name in blocks_data:
            block, created_flag = Block.objects.get_or_create(
                code=code,
                defaults={"name": name}
            )
            if created_flag:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created block: {code} - {name}"))
            else:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Block already exists: {code} - {name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created: {created}, Skipped (already existed): {skipped}"
            )
        )
