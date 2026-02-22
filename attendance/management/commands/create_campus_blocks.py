from django.core.management.base import BaseCommand
from attendance.models import Block


class Command(BaseCommand):
    help = "Create 36 campus blocks with predefined names and categories"

    def handle(self, *args, **options):
        blocks_data = [
            # 1-6: MBBs
            ("MBB-001", "Maharishi Block of Business - Block 1"),
            ("MBB-002", "Maharishi Block of Business - Block 2"),
            ("MBB-003", "Maharishi Block of Business - Block 3"),
            ("MBB-004", "Maharishi Block of Business - Block 4"),
            ("MBB-005", "Maharishi Block of Business - Block 5"),
            ("MBB-006", "Maharishi Block of Business - Block 6"),
            # 7-15: Agriculture and Fashion Designer
            ("AGR-007", "Agriculture Block - Block 7"),
            ("AGR-008", "Agriculture Block - Block 8"),
            ("AGR-009", "Agriculture Block - Block 9"),
            ("AGR-010", "Agriculture Block - Block 10"),
            ("AGR-011", "Agriculture Block - Block 11"),
            ("FD-012", "Fashion Design Block - Block 12"),
            ("FD-013", "Fashion Design Block - Block 13"),
            ("FD-014", "Fashion Design Block - Block 14"),
            ("FD-015", "Fashion Design Block - Block 15"),
            # 16-18: Administration Departments
            ("ADM-016", "Administration Block - Block 16"),
            ("ADM-017", "Administration Block - Block 17"),
            ("ADM-018", "Administration Block - Block 18"),
            # 19-21: Office of Vice Chancellor and Chancellor
            ("OVC-019", "Office of Vice Chancellor - Block 19"),
            ("OVC-020", "Office of Vice Chancellor - Block 20"),
            ("OC-021", "Office of Chancellor - Block 21"),
            # 22-26: Mechanical Engineering
            ("ME-022", "Mechanical Engineering Block - Block 22"),
            ("ME-023", "Mechanical Engineering Block - Block 23"),
            ("ME-024", "Mechanical Engineering Block - Block 24"),
            ("ME-025", "Mechanical Engineering Block - Block 25"),
            ("ME-026", "Mechanical Engineering Block - Block 26"),
            # 27-36: Computer Science and Engineering
            ("CSE-027", "Computer Science Engineering Block - Block 27"),
            ("CSE-028", "Computer Science Engineering Block - Block 28"),
            ("CSE-029", "Computer Science Engineering Block - Block 29"),
            ("CSE-030", "Computer Science Engineering Block - Block 30"),
            ("CSE-031", "Computer Science Engineering Block - Block 31"),
            ("CSE-032", "Computer Science Engineering Block - Block 32"),
            ("CSE-033", "Computer Science Engineering Block - Block 33"),
            ("CSE-034", "Computer Science Engineering Block - Block 34"),
            ("CSE-035", "Computer Science Engineering Block - Block 35"),
            ("CSE-036", "Computer Science Engineering Block - Block 36"),
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
