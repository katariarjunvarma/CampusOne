from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from food.models import FoodItem, Stall


class Command(BaseCommand):
    help = "Sync Stall records from FoodItem.stall_name/location and backfill FoodItem.stall FK."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print changes without writing to the database.",
        )
        parser.add_argument(
            "--no-backfill",
            action="store_true",
            help="Do not update FoodItem.stall FK (only create missing Stall rows).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        no_backfill = bool(options.get("no_backfill"))

        items = FoodItem.objects.all().only(
            "id", "stall_id", "stall_name", "location", "name"
        )

        created = 0
        linked = 0
        skipped = 0

        for it in items.iterator():
            stall_name = (it.stall_name or "").strip() or "Main Canteen"
            location = (it.location or "").strip() or "Campus Center"

            stall = Stall.objects.filter(name=stall_name, location=location).first()
            if not stall:
                created += 1
                self.stdout.write(
                    f"Create Stall: name='{stall_name}' location='{location}'"
                )
                if not dry_run:
                    stall = Stall.objects.create(name=stall_name, location=location)

            if no_backfill:
                skipped += 1
                continue

            if it.stall_id:
                skipped += 1
                continue

            if stall is None:
                skipped += 1
                continue

            linked += 1
            self.stdout.write(
                f"Link FoodItem #{it.id} '{it.name}' -> Stall '{stall_name}' ({location})"
            )
            if not dry_run:
                FoodItem.objects.filter(id=it.id).update(stall_id=stall.id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. stalls_created={created}, fooditems_linked={linked}, skipped={skipped}, dry_run={dry_run}"
            )
        )
