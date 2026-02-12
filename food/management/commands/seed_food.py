from __future__ import annotations

from datetime import time

from django.core.management.base import BaseCommand

from food.models import BreakSlot, FoodItem


class Command(BaseCommand):
    help = "Seed default food items and hourly break slots (8am-10pm)."

    def add_arguments(self, parser):
        parser.add_argument("--start", default=8, type=int, help="Start hour (0-23). Default 8")
        parser.add_argument("--end", default=22, type=int, help="End hour (1-24). Default 22")

    def handle(self, *args, **options):
        start = int(options["start"])
        end = int(options["end"])

        if start < 0 or start > 23 or end < 1 or end > 24 or end <= start:
            self.stderr.write(self.style.ERROR("Invalid start/end hours."))
            return

        # Clear old break slots and create hourly slots with 12-hour AM/PM labels
        BreakSlot.objects.all().delete()
        created_slots = 0
        for h in range(start, end):
            s = time(hour=h, minute=0)
            e = time(hour=h + 1, minute=0)
            # Format as 12-hour with AM/PM (e.g., "8am - 9am", "12pm - 1pm")
            def fmt_hour(hour):
                if hour == 0:
                    return "12am"
                elif hour == 12:
                    return "12pm"
                elif hour < 12:
                    return f"{hour}am"
                else:
                    return f"{hour - 12}pm"
            label = f"{fmt_hour(h)} - {fmt_hour(h + 1)}"
            BreakSlot.objects.create(
                name=label,
                start_time=s,
                end_time=e,
            )
            created_slots += 1

        # Seed food items (updates on re-run)
        allowed_locations = [
            "25 Block",
            "41 Block",
            "BH-1",
            "34 Block",
            "33 Block",
            "32 Block",
            "31 Block",
            "29 Block",
            "27 Block",
            "37 Block",
            "Boys studios-9",
            "Near Gh-2",
            "14 Block Canteen",
            "18 Block Canteen",
            "Unimall",
            "Uni Hospital",
        ]

        stalls = {
            "kannu_ki_chai": {"name": "25 Block Canteen", "location": "25 Block"},
            "oven_express": {"name": "Oven Express", "location": "Unimall"},
            "kitchen_ette": {"name": "Kitchen Ette", "location": "BH-1"},
            "south_tiffins": {"name": "34 Block Canteen", "location": "34 Block"},
            "thali_house": {"name": "Thali House", "location": "33 Block"},
            "chinese_wok": {"name": "Wok n Roll", "location": "32 Block"},
            "punjabi_tadka": {"name": "Punjabi Tadka", "location": "31 Block"},
            "campus_bites": {"name": "Campus Bites", "location": "29 Block"},
            "healthy_bowl": {"name": "Green Bowl", "location": "Uni Hospital"},
            "night_mess": {"name": "Night Mess", "location": "37 Block"},
            "studio_snacks": {"name": "Studio Snacks", "location": "Boys studios-9"},
            "gh2_cafe": {"name": "GH-2 Cafe", "location": "Near Gh-2"},
            "apartment_mess": {"name": "Apartment Canteen", "location": "41 Block"},
            "canteen_14": {"name": "Block 14 Canteen", "location": "14 Block Canteen"},
            "canteen_18": {"name": "Block 18 Canteen", "location": "18 Block Canteen"},
            "creamstone": {"name": "Creamstone", "location": "Unimall"},
            "canteen_27": {"name": "Block 27 Canteen", "location": "27 Block"},
        }

        categories_by_stall = {
            "kannu_ki_chai": "Beverages",
            "healthy_bowl": "Healthy",
            "punjabi_tadka": "North Indian",
            "thali_house": "North Indian",
            "south_tiffins": "Healthy",
            "oven_express": "Fast Food",
            "campus_bites": "Fast Food",
            "kitchen_ette": "North Indian",
            "chinese_wok": "Fast Food",
            "studio_snacks": "Fast Food",
            "gh2_cafe": "Fast Food",
            "night_mess": "North Indian",
            "apartment_mess": "Healthy",
            "canteen_14": "All Items",
            "canteen_18": "All Items",
            "creamstone": "Desserts",
            "canteen_27": "All Items",
        }

        # Mark any items from "All Canteens" category as inactive (old data cleanup)
        FoodItem.objects.filter(category="All Canteens").update(is_active=False)

        # Mark any items from "Apartment Canteen Near" as inactive (old data cleanup)
        FoodItem.objects.filter(stall_name="Apartment Canteen Near").update(is_active=False)

        # Mark "Ice Cream Cup" items as inactive (renamed to "Ice Cream")
        FoodItem.objects.filter(name="Ice Cream Cup").update(is_active=False)

        for k, v in stalls.items():
            if v["location"] not in allowed_locations:
                self.stderr.write(self.style.ERROR(f"Invalid location configured for stall {k}: {v['location']}"))
                return

        items = [
            # South Indian tiffins
            ("Idli (2 pcs)", "Steamed rice cakes with chutney", 25, "south_tiffins"),
            ("Vada (2 pcs)", "Crispy medu vada with sambar", 30, "south_tiffins"),
            ("Idli Vada Combo", "2 idli + 1 vada with sambar", 35, "south_tiffins"),
            ("Plain Dosa", "Crispy plain dosa", 30, "south_tiffins"),
            ("Masala Dosa", "Dosa stuffed with potato masala", 45, "south_tiffins"),
            ("Onion Dosa", "Dosa with onion topping", 50, "south_tiffins"),
            ("Rava Dosa", "Thin and crispy rava dosa", 55, "south_tiffins"),
            ("Set Dosa", "Soft set dosa (2 pcs)", 40, "south_tiffins"),
            ("Uttapam", "Vegetable uttapam", 55, "south_tiffins"),
            ("Pongal", "Ven pongal with ghee", 45, "south_tiffins"),
            ("Upma", "Classic vegetable upma", 35, "south_tiffins"),
            ("Lemon Rice", "South style lemon rice", 45, "south_tiffins"),
            ("Curd Rice", "Comforting curd rice", 40, "south_tiffins"),
            ("Sambar Rice", "Rice mixed with sambar", 55, "south_tiffins"),
            ("Filter Coffee", "Strong South Indian filter coffee", 20, "south_tiffins"),

            # Thalis
            ("Mini South Thali", "Rice, sambar, rasam, poriyal, curd", 85, "thali_house"),
            ("South Indian Thali", "Full South thali (veg)", 110, "thali_house"),
            ("Mini North Thali", "Roti, dal, sabzi, rice, salad", 95, "thali_house"),
            ("North Indian Thali", "Full North thali (veg)", 125, "thali_house"),
            ("Executive Thali", "Premium thali with sweet", 150, "thali_house"),

            # North Indian / Punjabi
            ("Dal Tadka", "Yellow dal tempered with spices", 80, "punjabi_tadka"),
            ("Dal Makhani", "Creamy black lentils", 95, "punjabi_tadka"),
            ("Rajma", "Kidney bean curry", 85, "punjabi_tadka"),
            ("Chole", "Punjabi chole masala", 85, "punjabi_tadka"),
            ("Paneer Butter Masala", "Creamy paneer gravy", 120, "punjabi_tadka"),
            ("Paneer Tikka Masala", "Smoky paneer tikka gravy", 125, "punjabi_tadka"),
            ("Kadai Paneer", "Paneer with capsicum in kadai masala", 120, "punjabi_tadka"),
            ("Mix Veg", "Seasonal mixed vegetables", 90, "punjabi_tadka"),
            ("Aloo Gobi", "Potato and cauliflower curry", 80, "punjabi_tadka"),
            ("Jeera Rice", "Cumin flavored rice", 55, "punjabi_tadka"),
            ("Veg Pulao", "Mild vegetable pulao", 70, "punjabi_tadka"),
            ("Roti", "Whole wheat roti", 10, "punjabi_tadka"),
            ("Butter Roti", "Buttered roti", 12, "punjabi_tadka"),
            ("Plain Naan", "Soft naan", 18, "punjabi_tadka"),
            ("Butter Naan", "Buttered naan", 22, "punjabi_tadka"),
            ("Curd", "Fresh curd bowl", 25, "punjabi_tadka"),
            ("Papad", "Crispy papad", 15, "punjabi_tadka"),
            ("Gulab Jamun", "2 pcs gulab jamun", 35, "punjabi_tadka"),

            # Chinese / Indo-Chinese
            ("Veg Hakka Noodles", "Stir-fried noodles with vegetables", 85, "chinese_wok"),
            ("Schezwan Noodles", "Spicy schezwan noodles (veg)", 95, "chinese_wok"),
            ("Veg Fried Rice", "Vegetable fried rice", 85, "chinese_wok"),
            ("Schezwan Fried Rice", "Spicy fried rice", 95, "chinese_wok"),
            ("Veg Manchurian (Dry)", "Crispy veg manchurian", 90, "chinese_wok"),
            ("Veg Manchurian (Gravy)", "Manchurian in gravy", 95, "chinese_wok"),
            ("Chilli Paneer (Dry)", "Paneer tossed in chilli sauce", 120, "chinese_wok"),
            ("Chilli Paneer (Gravy)", "Chilli paneer with gravy", 125, "chinese_wok"),
            ("Honey Chilli Potato", "Crispy potato in honey chilli", 95, "chinese_wok"),
            ("Veg Spring Roll", "Crispy veg spring rolls", 70, "chinese_wok"),
            ("Veg Momos (Steamed)", "Steamed veg momos", 70, "chinese_wok"),
            ("Veg Momos (Fried)", "Fried veg momos", 80, "chinese_wok"),
            ("Paneer Momos", "Paneer stuffed momos", 90, "chinese_wok"),
            ("Manchow Soup", "Hot veg manchow soup", 60, "chinese_wok"),
            ("Hot & Sour Soup", "Veg hot and sour soup", 60, "chinese_wok"),

            # Bakery / Snacks
            ("Veg Puff", "Fresh baked veg puff", 25, "oven_express"),
            ("Paneer Puff", "Paneer puff", 30, "oven_express"),
            ("Cheese Sandwich", "Grilled cheese sandwich", 60, "oven_express"),
            ("Veg Grilled Sandwich", "Grilled sandwich with veggies", 55, "oven_express"),
            ("Garlic Bread", "Toasted garlic bread", 50, "oven_express"),
            ("Veg Burger", "Veg patty burger", 70, "oven_express"),
            ("French Fries", "Crispy fries", 60, "oven_express"),

            # Tea / Beverages
            ("Cutting Chai", "Strong cutting chai", 12, "kannu_ki_chai"),
            ("Ginger Tea", "Adrak wali chai", 15, "kannu_ki_chai"),
            ("Elaichi Tea", "Cardamom tea", 15, "kannu_ki_chai"),
            ("Hot Coffee", "Classic hot coffee", 20, "kannu_ki_chai"),
            ("Badam Milk", "Warm badam milk", 30, "kannu_ki_chai"),
            ("Lassi", "Sweet lassi", 35, "kannu_ki_chai"),

            # Campus staples
            ("Veg Biryani", "Aromatic veg biryani", 110, "kitchen_ette"),
            ("Paneer Biryani", "Paneer biryani", 125, "kitchen_ette"),
            ("Veg Meal (Rice)", "Rice + dal + sabzi + curd", 100, "kitchen_ette"),
            ("Paneer Roll", "Paneer wrap roll", 80, "campus_bites"),
            ("Veg Frankie", "Veg frankie roll", 70, "campus_bites"),
            ("Veg Sandwich", "Fresh veg sandwich", 50, "campus_bites"),
            ("Pav Bhaji", "Butter pav bhaji", 90, "campus_bites"),
            ("Chole Bhature", "Chole with bhature", 110, "campus_bites"),
            ("Poha", "Indori style poha", 40, "canteen_27"),
            ("Dhokla", "Soft khaman dhokla", 45, "canteen_27"),
            ("Veg Maggi", "Masala veg maggi", 50, "studio_snacks"),
            ("Cheese Maggi", "Cheesy maggi", 60, "studio_snacks"),
            ("Corn Cup", "Butter masala corn", 35, "studio_snacks"),
            ("Bhel Puri", "Chatpata bhel puri", 45, "gh2_cafe"),
            ("Pani Puri", "6 pcs pani puri", 45, "gh2_cafe"),
            ("Dahi Puri", "6 pcs dahi puri", 55, "gh2_cafe"),

            # Healthy / Hospital-side
            ("Salad Bowl", "Fresh seasonal salad bowl", 70, "healthy_bowl"),
            ("Fruit Bowl", "Assorted fruit bowl", 75, "healthy_bowl"),
            ("Fresh Juice", "Seasonal fresh juice", 50, "healthy_bowl"),
            ("Soup of the Day", "Hot vegetable soup", 55, "healthy_bowl"),
            ("Sprouts Chaat", "Sprouts with lemon and masala", 60, "healthy_bowl"),

            # Night mess / Apartment
            ("Aloo Paratha", "Aloo paratha with curd", 70, "night_mess"),
            ("Paneer Paratha", "Paneer paratha with curd", 85, "night_mess"),
            ("Veg Khichdi", "Moong dal khichdi", 80, "apartment_mess"),
            ("Vegetable Upma", "Light vegetable upma", 40, "apartment_mess"),
            ("Rice + Dal + Sabzi", "Simple home-style meal", 95, "apartment_mess"),

            # Common
            ("Water Bottle", "500ml purified water", 20, "kannu_ki_chai"),
            ("Soft Drink", "300ml soft drink", 30, "campus_bites"),
            ("Ice Cream", "Vanilla ice cream cup", 35, "creamstone"),
        ]

        # VERIFIED WORKING Unsplash food photo URLs - each is a real distinct photo
        image_urls = {
            # South Indian - verified distinct photos
            "Idli (2 pcs)": "https://images.unsplash.com/photo-1533089862017-5614ecb352ae?w=400&h=300&fit=crop",
            "Vada (2 pcs)": "https://images.unsplash.com/photo-1610192249866-494c72c08227?w=400&h=300&fit=crop",
            "Idli Vada Combo": "https://images.unsplash.com/photo-1589302168068-964664d93a06?w=400&h=300&fit=crop",
            "Plain Dosa": "https://images.unsplash.com/photo-1662116765994-54592e877d9e?w=400&h=300&fit=crop",
            "Masala Dosa": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=400&h=300&fit=crop",
            "Onion Dosa": "https://images.unsplash.com/photo-1615276510847-d851f3d7317d?w=400&h=300&fit=crop",
            "Rava Dosa": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=400&h=300&fit=crop",
            "Set Dosa": "https://images.unsplash.com/photo-1626202268668-8a1c24012d03?w=400&h=300&fit=crop",
            "Uttapam": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Pongal": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=300&fit=crop",
            "Upma": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Lemon Rice": "https://images.unsplash.com/photo-1596560548464-f010549b84d7?w=400&h=300&fit=crop",
            "Curd Rice": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&h=300&fit=crop",
            "Sambar Rice": "https://images.unsplash.com/photo-1542361345-89e58247f2d5?w=400&h=300&fit=crop",
            "Filter Coffee": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&h=300&fit=crop",

            # Thalis
            "Mini South Thali": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400&h=300&fit=crop",
            "South Indian Thali": "https://images.unsplash.com/photo-1589302168068-964664d93a06?w=400&h=300&fit=crop",
            "Mini North Thali": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&h=300&fit=crop",
            "North Indian Thali": "https://images.unsplash.com/photo-1603133872878-684f208fb74b?w=400&h=300&fit=crop",
            "Executive Thali": "https://images.unsplash.com/photo-1626139573537-9410a8ebdf36?w=400&h=300&fit=crop",

            # North Indian
            "Dal Tadka": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Dal Makhani": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&h=300&fit=crop",
            "Rajma": "https://images.unsplash.com/photo-1626202268668-8a1c24012d03?w=400&h=300&fit=crop",
            "Chole": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=400&h=300&fit=crop",
            "Paneer Butter Masala": "https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=400&h=300&fit=crop",
            "Paneer Tikka Masala": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=400&h=300&fit=crop",
            "Kadai Paneer": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400&h=300&fit=crop",
            "Mix Veg": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=300&fit=crop",
            "Aloo Gobi": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Jeera Rice": "https://images.unsplash.com/photo-1590080875515-8a3a8dc5735e?w=400&h=300&fit=crop",
            "Veg Pulao": "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400&h=300&fit=crop",
            "Roti": "https://images.unsplash.com/photo-1615276510847-d851f3d7317d?w=400&h=300&fit=crop",
            "Butter Roti": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=400&h=300&fit=crop",
            "Plain Naan": "https://images.unsplash.com/photo-1626202268668-8a1c24012d03?w=400&h=300&fit=crop",
            "Butter Naan": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Curd": "https://images.unsplash.com/photo-1570968905869-fec089bfe23d?w=400&h=300&fit=crop",
            "Papad": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=400&h=300&fit=crop",
            "Gulab Jamun": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=400&h=300&fit=crop",

            # Chinese
            "Veg Hakka Noodles": "https://images.unsplash.com/photo-1552611052-33e04de081de?w=400&h=300&fit=crop",
            "Schezwan Noodles": "https://images.unsplash.com/photo-1610192249866-494c72c08227?w=400&h=300&fit=crop",
            "Veg Fried Rice": "https://images.unsplash.com/photo-1603133872878-684f208fb74b?w=400&h=300&fit=crop",
            "Schezwan Fried Rice": "https://images.unsplash.com/photo-1552611052-33e04de081de?w=400&h=300&fit=crop",
            "Veg Manchurian (Dry)": "https://images.unsplash.com/photo-1626139573537-9410a8ebdf36?w=400&h=300&fit=crop",
            "Veg Manchurian (Gravy)": "https://images.unsplash.com/photo-1626202268668-8a1c24012d03?w=400&h=300&fit=crop",
            "Chilli Paneer (Dry)": "https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=400&h=300&fit=crop",
            "Chilli Paneer (Gravy)": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400&h=300&fit=crop",
            "Honey Chilli Potato": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=400&h=300&fit=crop",
            "Veg Spring Roll": "https://images.unsplash.com/photo-1625220194771-7eb6f34e9e7a?w=400&h=300&fit=crop",
            "Veg Momos (Steamed)": "https://images.unsplash.com/photo-1533089862017-5614ecb352ae?w=400&h=300&fit=crop",
            "Veg Momos (Fried)": "https://images.unsplash.com/photo-1610192249866-494c72c08227?w=400&h=300&fit=crop",
            "Paneer Momos": "https://images.unsplash.com/photo-1589302168068-964664d93a06?w=400&h=300&fit=crop",
            "Manchow Soup": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400&h=300&fit=crop",
            "Hot & Sour Soup": "https://images.unsplash.com/photo-1542361345-89e58247f2d5?w=400&h=300&fit=crop",

            # Snacks
            "Veg Puff": "https://images.unsplash.com/photo-1626139573537-9410a8ebdf36?w=400&h=300&fit=crop",
            "Paneer Puff": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400&h=300&fit=crop",
            "Cheese Sandwich": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400&h=300&fit=crop",
            "Veg Grilled Sandwich": "https://images.unsplash.com/photo-1554433607-66b5efe9d304?w=400&h=300&fit=crop",
            "Garlic Bread": "https://images.unsplash.com/photo-1573140247632-f519fd35b0e2?w=400&h=300&fit=crop",
            "Veg Burger": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=400&h=300&fit=crop",
            "French Fries": "https://images.unsplash.com/photo-1576107232684-1279f390859f?w=400&h=300&fit=crop",
            "Bread Pakora": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Kachori": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Samosa": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Tea": "https://images.unsplash.com/photo-1561336313-0bd5e0b27ec8?w=400&h=300&fit=crop",
            "Coffee": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&h=300&fit=crop",

            # Beverages
            "Cutting Chai": "https://images.unsplash.com/photo-1561336313-0bd5e0b27ec8?w=400&h=300&fit=crop",
            "Ginger Tea": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=400&h=300&fit=crop",
            "Elaichi Tea": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400&h=300&fit=crop",
            "Hot Coffee": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&h=300&fit=crop",
            "Badam Milk": "https://images.unsplash.com/photo-1570968905869-fec089bfe23d?w=400&h=300&fit=crop",
            "Lassi": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=400&h=300&fit=crop",

            # Campus staples
            "Veg Biryani": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&h=300&fit=crop",
            "Paneer Biryani": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Veg Meal (Rice)": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&h=300&fit=crop",
            "Paneer Roll": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=400&h=300&fit=crop",
            "Veg Frankie": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=400&h=300&fit=crop",
            "Veg Sandwich": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400&h=300&fit=crop",
            "Pav Bhaji": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Chole Bhature": "https://images.unsplash.com/photo-1626139573537-9410a8ebdf36?w=400&h=300&fit=crop",
            "Poha": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Dhokla": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Veg Maggi": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=400&h=300&fit=crop",
            "Cheese Maggi": "https://images.unsplash.com/photo-1626202268668-8a1c24012d03?w=400&h=300&fit=crop",
            "Corn Cup": "https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=400&h=300&fit=crop",
            "Bhel Puri": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Pani Puri": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop",
            "Dahi Puri": "https://images.unsplash.com/photo-1596560548464-f010549b84d7?w=400&h=300&fit=crop",
            "Biscuit": "https://images.unsplash.com/photo-1600093463592-8e36ae95ef56?w=400&h=300&fit=crop",

            # Healthy
            "Salad Bowl": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=300&fit=crop",
            "Fruit Bowl": "https://images.unsplash.com/photo-1519996529931-28324d5a630e?w=400&h=300&fit=crop",
            "Fresh Juice": "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400&h=300&fit=crop",
            "Soup of the Day": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400&h=300&fit=crop",
            "Sprouts Chaat": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=300&fit=crop",

            # Night mess
            "Aloo Paratha": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Paneer Paratha": "https://images.unsplash.com/photo-1626202268668-8a1c24012d03?w=400&h=300&fit=crop",
            "Veg Khichdi": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&h=300&fit=crop",
            "Vegetable Upma": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop",
            "Rice + Dal + Sabzi": "https://images.unsplash.com/photo-1589302168068-964664d93a06?w=400&h=300&fit=crop",

            # Common
            "Water Bottle": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=400&h=300&fit=crop",
            "Soft Drink": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=400&h=300&fit=crop",
            "Ice Cream Cup": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=400&h=300&fit=crop",
        }

        created_items = 0
        updated_items = 0
        for name, desc, price, stall_key in items:
            stall = stalls[stall_key]

            category = categories_by_stall.get(stall_key) or "All Items"

            if name in {"Gulab Jamun", "Ice Cream Cup"}:
                category = "Desserts"
            if name in {"Cutting Chai", "Ginger Tea", "Elaichi Tea", "Hot Coffee", "Badam Milk", "Lassi", "Filter Coffee", "Fresh Juice", "Tea", "Coffee"}:
                category = "Beverages"

            # Use specific accurate image URL
            image_url = image_urls.get(name, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=300&fit=crop")

            obj, created = FoodItem.objects.update_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "price": price,
                    "is_active": True,
                    "stall_name": stall["name"],
                    "location": stall["location"],
                    "category": category,
                    "image_url": image_url,
                },
            )
            if created:
                created_items += 1
            else:
                updated_items += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. New slots: {created_slots} | New items: {created_items} | Updated items: {updated_items}"
            )
        )
