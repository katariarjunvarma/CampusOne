from django.core.management.base import BaseCommand
from attendance.models import Block


class Command(BaseCommand):
    help = "Update block names by category while keeping codes unchanged"

    def handle(self, *args, **options):
        # Define mappings
        name_map = {
            # 1-6: MBBs
            "BLOCK-1": "Maharishi Block of Business - Block 1",
            "BLOCK-2": "Maharishi Block of Business - Block 2",
            "BLOCK-3": "Maharishi Block of Business - Block 3",
            "BLOCK-4": "Maharishi Block of Business - Block 4",
            "BLOCK-5": "Maharishi Block of Business - Block 5",
            "BLOCK-6": "Maharishi Block of Business - Block 6",
            # 7-15: Agriculture and Fashion Designer
            "BLOCK-7": "Agriculture Block - Block 7",
            "BLOCK-8": "Agriculture Block - Block 8",
            "BLOCK-9": "Agriculture Block - Block 9",
            "BLOCK-10": "Agriculture Block - Block 10",
            "BLOCK-11": "Agriculture Block - Block 11",
            "BLOCK-12": "Fashion Design Block - Block 12",
            "BLOCK-13": "Fashion Design Block - Block 13",
            "BLOCK-14": "Fashion Design Block - Block 14",
            "BLOCK-15": "Fashion Design Block - Block 15",
            # 16-18: Administration Departments
            "BLOCK-16": "Administration Block - Block 16",
            "BLOCK-17": "Administration Block - Block 17",
            "BLOCK-18": "Administration Block - Block 18",
            # 19-21: Office of Vice Chancellor and Chancellor
            "BLOCK-19": "Office of Vice Chancellor - Block 19",
            "BLOCK-20": "Office of Vice Chancellor - Block 20",
            "BLOCK-21": "Office of Chancellor - Block 21",
            # 22-26: Mechanical Engineering
            "BLOCK-22": "Mechanical Engineering Block - Block 22",
            "BLOCK-23": "Mechanical Engineering Block - Block 23",
            "BLOCK-24": "Mechanical Engineering Block - Block 24",
            "BLOCK-25": "Mechanical Engineering Block - Block 25",
            "BLOCK-26": "Mechanical Engineering Block - Block 26",
            # 27-36: Computer Science and Engineering
            "BLOCK-27": "Computer Science Engineering Block - Block 27",
            "BLOCK-28": "Computer Science Engineering Block - Block 28",
            "BLOCK-29": "Computer Science Engineering Block - Block 29",
            "BLOCK-30": "Computer Science Engineering Block - Block 30",
            "BLOCK-31": "Computer Science Engineering Block - Block 31",
            "BLOCK-32": "Computer Science Engineering Block - Block 32",
            "BLOCK-33": "Computer Science Engineering Block - Block 33",
            "BLOCK-34": "Computer Science Engineering Block - Block 34",
            "BLOCK-35": "Computer Science Engineering Block - Block 35",
            "BLOCK-36": "Computer Science Engineering Block - Block 36",
            # Extra blocks
            "ECAH": "ECAH Block",
            "EVRY": "EVRY Block",
        }

        updated = 0
        skipped = 0
        for block in Block.objects.all():
            if block.code in name_map:
                if block.name != name_map[block.code]:
                    block.name = name_map[block.code]
                    block.save(update_fields=["name"])
                    updated += 1
                    self.stdout.write(self.style.SUCCESS(f"Updated {block.code}: {block.name}"))
                else:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"No change needed for {block.code}: {block.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Updated: {updated}, Skipped (no change): {skipped}"
            )
        )
