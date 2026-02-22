from django.core.management.base import BaseCommand
from attendance.models import Block


class Command(BaseCommand):
    help = "Clean block names (remove 'Block X' suffix) and ensure codes are Block-1 to Block-36"

    def handle(self, *args, **options):
        # Define clean names (no 'Block X' suffix)
        name_map = {
            # 1-6: MBBs
            "BLOCK-1": "Maharishi Block of Business",
            "BLOCK-2": "Maharishi Block of Business",
            "BLOCK-3": "Maharishi Block of Business",
            "BLOCK-4": "Maharishi Block of Business",
            "BLOCK-5": "Maharishi Block of Business",
            "BLOCK-6": "Maharishi Block of Business",
            # 7-15: Agriculture and Fashion Designer
            "BLOCK-7": "Agriculture",
            "BLOCK-8": "Agriculture",
            "BLOCK-9": "Agriculture",
            "BLOCK-10": "Agriculture",
            "BLOCK-11": "Agriculture",
            "BLOCK-12": "Fashion Design",
            "BLOCK-13": "Fashion Design",
            "BLOCK-14": "Fashion Design",
            "BLOCK-15": "Fashion Design",
            # 16-18: Administration Departments
            "BLOCK-16": "Administration",
            "BLOCK-17": "Administration",
            "BLOCK-18": "Administration",
            # 19-21: Office of Vice Chancellor and Chancellor
            "BLOCK-19": "Office of Vice Chancellor",
            "BLOCK-20": "Office of Vice Chancellor",
            "BLOCK-21": "Office of Chancellor",
            # 22-26: Mechanical Engineering
            "BLOCK-22": "Mechanical Engineering",
            "BLOCK-23": "Mechanical Engineering",
            "BLOCK-24": "Mechanical Engineering",
            "BLOCK-25": "Mechanical Engineering",
            "BLOCK-26": "Mechanical Engineering",
            # 27-36: Computer Science and Engineering
            "BLOCK-27": "Computer Science Engineering",
            "BLOCK-28": "Computer Science Engineering",
            "BLOCK-29": "Computer Science Engineering",
            "BLOCK-30": "Computer Science Engineering",
            "BLOCK-31": "Computer Science Engineering",
            "BLOCK-32": "Computer Science Engineering",
            "BLOCK-33": "Computer Science Engineering",
            "BLOCK-34": "Computer Science Engineering",
            "BLOCK-35": "Computer Science Engineering",
            "BLOCK-36": "Computer Science Engineering",
            # Extra blocks
            "ECAH": "ECAH",
            "EVRY": "EVRY",
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
