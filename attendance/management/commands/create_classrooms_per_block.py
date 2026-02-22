from django.core.management.base import BaseCommand
from attendance.models import Block, Classroom
import random


class Command(BaseCommand):
    help = "Create 10 classrooms per block with 3-digit room numbers and capacity 60-77"

    def handle(self, *args, **options):
        blocks = Block.objects.filter(code__regex=r'^BLOCK-[0-9]+$').order_by('code')
        created = 0
        skipped = 0

        for block in blocks:
            # Generate 10 unique room numbers for this block
            room_numbers = set()
            while len(room_numbers) < 10:
                floor = random.randint(1, 6)
                room_idx = random.randint(1, 10)
                room_num = f"{floor}{room_idx:02d}"
                room_numbers.add(room_num)

            for room_num in sorted(room_numbers):
                capacity = random.randint(60, 77)
                room_number = f"{block.code}-{room_num}"
                classroom, created_flag = Classroom.objects.get_or_create(
                    block=block,
                    room_number=room_number,
                    defaults={"capacity": capacity}
                )
                if created_flag:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created classroom: {room_number} (capacity {capacity}) in {block.code}"
                        )
                    )
                else:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Classroom already exists: {room_number} in {block.code}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created: {created}, Skipped (already existed): {skipped}"
            )
        )
