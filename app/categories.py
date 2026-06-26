"""Canonical category taxonomy, colours and the starter rule set.

This module is the single source of truth for *what* categories exist. A
category has a top-level name (e.g. "Transport") and a set of subcategories
(e.g. "Fuel", "Parking"). The dashboards colour-code by top-level category, so
a stable colour map lives here too.

``STARTER_RULES`` is a pragmatic, real-world list of ``(pattern, category,
subcategory)`` tuples used to auto-categorize common merchants. Patterns are
matched case-insensitively as substrings of the transaction description.
"""

# Default bucket for transactions no rule has classified yet.
UNCATEGORIZED = "Uncategorized"

# Top-level category -> list of subcategories. Order is used in the UI.
TAXONOMY: dict[str, list[str]] = {
    "Food & Drink": [
        "Groceries",
        "Restaurants & Cafés",
        "Fast Food",
        "Food Delivery",
        "Bars & Nightlife",
    ],
    "Transport": [
        "Fuel",
        "Ride-hailing & Taxi",
        "Public Transport",
        "Trains",
        "Flights",
        "Car Rental",
        "Parking",
        "Tolls",
        "Car Wash & Maintenance",
    ],
    "Travel": [
        "Hotels & Lodging",
        "Airbnb",
        "Attractions",
        "Duty Free",
    ],
    "Shopping": [
        "Online Shopping",
        "Clothing",
        "Electronics",
        "General",
    ],
    "Health & Fitness": [
        "Sports & Recreation",
        "Drugstore & Pharmacy",
        "Healthcare",
    ],
    "Bills & Utilities": [
        "Software & Subscriptions",
        "Phone & Internet",
        "Utilities",
    ],
    "Entertainment": [
        "Streaming",
        "Events & Tickets",
    ],
    "Housing": [
        "Rent",
        "Home",
    ],
    "Income": [
        "Salary",
        "Refunds",
        "Other Income",
    ],
    "Fees & Charges": [
        "Bank Fees",
    ],
    "Other": [
        "Misc",
    ],
}

# Stable, pleasant colour per top-level category (used across all charts).
CATEGORY_COLORS: dict[str, str] = {
    "Food & Drink": "#ef4444",
    "Transport": "#3b82f6",
    "Travel": "#8b5cf6",
    "Shopping": "#ec4899",
    "Health & Fitness": "#22c55e",
    "Bills & Utilities": "#f59e0b",
    "Entertainment": "#06b6d4",
    "Housing": "#a16207",
    "Income": "#10b981",
    "Fees & Charges": "#64748b",
    "Other": "#94a3b8",
    UNCATEGORIZED: "#cbd5e1",
}


def all_categories(include_uncategorized: bool = True) -> list[str]:
    """Return all top-level category names."""
    cats = list(TAXONOMY.keys())
    if include_uncategorized:
        cats.append(UNCATEGORIZED)
    return cats


def subcategories(category: str) -> list[str]:
    """Return the subcategories defined for a top-level category."""
    return TAXONOMY.get(category, [])


def all_subcategories() -> list[str]:
    """Return every subcategory across the whole taxonomy (sorted, unique)."""
    subs: set[str] = set()
    for values in TAXONOMY.values():
        subs.update(values)
    return sorted(subs)


def color_for(category: str) -> str:
    """Return the chart colour for a top-level category (grey fallback)."""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["Other"])


# --------------------------------------------------------------------------- #
# Starter rules: (pattern, category, subcategory)
# Patterns are lower-cased substrings matched against the description.
# Ordered most-specific first so the first match wins.
# --------------------------------------------------------------------------- #
STARTER_RULES: list[tuple[str, str, str]] = [
    # --- Fuel / petrol stations ---
    ("tankstelle", "Transport", "Fuel"),
    ("shell", "Transport", "Fuel"),
    ("omv", "Transport", "Fuel"),
    ("bp ", "Transport", "Fuel"),
    ("aral", "Transport", "Fuel"),
    ("avia", "Transport", "Fuel"),
    ("orlen", "Transport", "Fuel"),
    ("eni", "Transport", "Fuel"),
    ("petrol", "Transport", "Fuel"),
    ("oil mini mart", "Transport", "Fuel"),
    # --- Ride-hailing & taxi ---
    ("uber", "Transport", "Ride-hailing & Taxi"),
    ("bolt", "Transport", "Ride-hailing & Taxi"),
    ("careem", "Transport", "Ride-hailing & Taxi"),
    ("yandex", "Transport", "Ride-hailing & Taxi"),
    ("taxi", "Transport", "Ride-hailing & Taxi"),
    # --- Trains & public transport ---
    ("trainline", "Transport", "Trains"),
    ("oebb", "Transport", "Trains"),
    ("öbb", "Transport", "Trains"),
    ("sncf", "Transport", "Trains"),
    ("railjet", "Transport", "Trains"),
    ("wiener linien", "Transport", "Public Transport"),
    ("sbb", "Transport", "Public Transport"),
    # --- Flights ---
    ("austrian", "Transport", "Flights"),
    ("jetblue", "Transport", "Flights"),
    ("kiwi", "Transport", "Flights"),
    ("ryanair", "Transport", "Flights"),
    ("lufthansa", "Transport", "Flights"),
    ("emirates", "Transport", "Flights"),
    ("wizz", "Transport", "Flights"),
    ("eurowings", "Transport", "Flights"),
    # --- Parking ---
    ("parkhaus", "Transport", "Parking"),
    ("parkgarage", "Transport", "Parking"),
    ("parkingpay", "Transport", "Parking"),
    ("parkings", "Transport", "Parking"),
    ("parking", "Transport", "Parking"),
    ("indigo", "Transport", "Parking"),
    ("q-park", "Transport", "Parking"),
    ("valet", "Transport", "Parking"),
    # --- Tolls ---
    ("escota", "Transport", "Tolls"),
    ("autoroute", "Transport", "Tolls"),
    ("telepeage", "Transport", "Tolls"),
    ("asfinag", "Transport", "Tolls"),
    ("vignette", "Transport", "Tolls"),
    # --- Car wash & maintenance ---
    ("autow scherei", "Transport", "Car Wash & Maintenance"),
    ("autowaescherei", "Transport", "Car Wash & Maintenance"),
    ("autowäscherei", "Transport", "Car Wash & Maintenance"),
    ("car wash", "Transport", "Car Wash & Maintenance"),
    ("werkstatt", "Transport", "Car Wash & Maintenance"),
    # --- Groceries ---
    ("billa", "Food & Drink", "Groceries"),
    ("spar", "Food & Drink", "Groceries"),
    ("interspar", "Food & Drink", "Groceries"),
    ("migros", "Food & Drink", "Groceries"),
    ("hofer", "Food & Drink", "Groceries"),
    ("lidl", "Food & Drink", "Groceries"),
    ("aldi", "Food & Drink", "Groceries"),
    ("etsan", "Food & Drink", "Groceries"),
    ("market pointe", "Food & Drink", "Groceries"),
    ("selecta", "Food & Drink", "Groceries"),
    ("tabak", "Food & Drink", "Groceries"),
    # --- Fast food ---
    ("mcdonald", "Food & Drink", "Fast Food"),
    ("burger king", "Food & Drink", "Fast Food"),
    ("kfc", "Food & Drink", "Fast Food"),
    ("doner", "Food & Drink", "Fast Food"),
    ("döner", "Food & Drink", "Fast Food"),
    ("kebap", "Food & Drink", "Fast Food"),
    ("kebab", "Food & Drink", "Fast Food"),
    ("grill", "Food & Drink", "Fast Food"),
    ("pizza", "Food & Drink", "Fast Food"),
    ("subway", "Food & Drink", "Fast Food"),
    # --- Food delivery ---
    ("foodora", "Food & Drink", "Food Delivery"),
    ("talabat", "Food & Drink", "Food Delivery"),
    ("glovo", "Food & Drink", "Food Delivery"),
    ("deliveroo", "Food & Drink", "Food Delivery"),
    ("lieferando", "Food & Drink", "Food Delivery"),
    # --- Restaurants & cafés ---
    ("restaurant", "Food & Drink", "Restaurants & Cafés"),
    ("cafe", "Food & Drink", "Restaurants & Cafés"),
    ("café", "Food & Drink", "Restaurants & Cafés"),
    ("tst ", "Food & Drink", "Restaurants & Cafés"),
    ("gourmet", "Food & Drink", "Restaurants & Cafés"),
    ("coffee", "Food & Drink", "Restaurants & Cafés"),
    ("starbucks", "Food & Drink", "Restaurants & Cafés"),
    # --- Bars & nightlife ---
    ("bar ", "Food & Drink", "Bars & Nightlife"),
    ("lounge", "Food & Drink", "Bars & Nightlife"),
    ("pub", "Food & Drink", "Bars & Nightlife"),
    ("club", "Food & Drink", "Bars & Nightlife"),
    # --- Travel: hotels / lodging ---
    ("airbnb", "Travel", "Airbnb"),
    ("radisson", "Travel", "Hotels & Lodging"),
    ("sol melia", "Travel", "Hotels & Lodging"),
    ("melia", "Travel", "Hotels & Lodging"),
    ("hotel", "Travel", "Hotels & Lodging"),
    ("marriott", "Travel", "Hotels & Lodging"),
    ("hilton", "Travel", "Hotels & Lodging"),
    ("ibis", "Travel", "Hotels & Lodging"),
    # --- Travel: attractions / duty free ---
    ("theme park", "Travel", "Attractions"),
    ("studio city", "Travel", "Attractions"),
    ("museum", "Travel", "Attractions"),
    ("duty free", "Travel", "Duty Free"),
    ("heinemann", "Travel", "Duty Free"),
    # --- Shopping ---
    ("amzn", "Shopping", "Online Shopping"),
    ("amazon", "Shopping", "Online Shopping"),
    ("zalando", "Shopping", "Clothing"),
    ("h&m", "Shopping", "Clothing"),
    ("zara", "Shopping", "Clothing"),
    ("mediamarkt", "Shopping", "Electronics"),
    ("apple.com", "Shopping", "Electronics"),
    ("ikea", "Shopping", "General"),
    # --- Health & fitness ---
    ("eversports", "Health & Fitness", "Sports & Recreation"),
    ("playtomic", "Health & Fitness", "Sports & Recreation"),
    ("padel", "Health & Fitness", "Sports & Recreation"),
    ("gym", "Health & Fitness", "Sports & Recreation"),
    ("fitness", "Health & Fitness", "Sports & Recreation"),
    ("apotheke", "Health & Fitness", "Drugstore & Pharmacy"),
    ("pharmacy", "Health & Fitness", "Drugstore & Pharmacy"),
    ("bipa", "Health & Fitness", "Drugstore & Pharmacy"),
    ("dm fil", "Health & Fitness", "Drugstore & Pharmacy"),
    ("function health", "Health & Fitness", "Healthcare"),
    ("remedy place", "Health & Fitness", "Healthcare"),
    ("clinic", "Health & Fitness", "Healthcare"),
    ("dental", "Health & Fitness", "Healthcare"),
    # --- Bills & utilities: software / subscriptions ---
    ("claude", "Bills & Utilities", "Software & Subscriptions"),
    ("replit", "Bills & Utilities", "Software & Subscriptions"),
    ("cloudflare", "Bills & Utilities", "Software & Subscriptions"),
    ("redis", "Bills & Utilities", "Software & Subscriptions"),
    ("mongodb", "Bills & Utilities", "Software & Subscriptions"),
    ("openai", "Bills & Utilities", "Software & Subscriptions"),
    ("github", "Bills & Utilities", "Software & Subscriptions"),
    ("vercel", "Bills & Utilities", "Software & Subscriptions"),
    ("notion", "Bills & Utilities", "Software & Subscriptions"),
    ("google", "Bills & Utilities", "Software & Subscriptions"),
    # --- Entertainment ---
    ("netflix", "Entertainment", "Streaming"),
    ("spotify", "Entertainment", "Streaming"),
    ("disney", "Entertainment", "Streaming"),
    ("youtube", "Entertainment", "Streaming"),
    ("future events", "Entertainment", "Events & Tickets"),
    ("eventim", "Entertainment", "Events & Tickets"),
    ("citymatine", "Entertainment", "Events & Tickets"),
    ("ticket", "Entertainment", "Events & Tickets"),
    ("cinema", "Entertainment", "Events & Tickets"),
    ("kino", "Entertainment", "Events & Tickets"),
    # --- Housing ---
    ("rent payment", "Housing", "Rent"),
    ("miete", "Housing", "Rent"),
    # --- Income ---
    ("salary", "Income", "Salary"),
    ("gehalt", "Income", "Salary"),
    ("payroll", "Income", "Salary"),
    ("refund", "Income", "Refunds"),
    # --- Extra merchants observed in real statements -----------------------
    # Car rental
    ("rent a car", "Transport", "Car Rental"),
    ("car rental", "Transport", "Car Rental"),
    ("sixt", "Transport", "Car Rental"),
    ("thrifty", "Transport", "Car Rental"),
    ("turo ", "Transport", "Car Rental"),
    ("hertz", "Transport", "Car Rental"),
    ("europcar", "Transport", "Car Rental"),
    ("avis", "Transport", "Car Rental"),
    # More fuel
    ("turmoel", "Transport", "Fuel"),
    ("turmöl", "Transport", "Fuel"),
    ("waschstrasse", "Transport", "Car Wash & Maintenance"),
    ("waschstraße", "Transport", "Car Wash & Maintenance"),
    # More parking
    ("parken", "Transport", "Parking"),
    # More flights
    ("mytrip", "Transport", "Flights"),
    ("emirate", "Transport", "Flights"),
    ("azal", "Transport", "Flights"),
    # More groceries
    ("supermarket", "Food & Drink", "Groceries"),
    ("mini mart", "Food & Drink", "Groceries"),
    ("full cart", "Food & Drink", "Groceries"),
    # More fast food / restaurants
    ("doener", "Food & Drink", "Fast Food"),
    ("do co", "Food & Drink", "Restaurants & Cafés"),
    ("raclette", "Food & Drink", "Restaurants & Cafés"),
    # Hotels & travel
    ("front office", "Travel", "Hotels & Lodging"),
    ("waldorf astoria", "Travel", "Hotels & Lodging"),
    ("so vienna", "Travel", "Hotels & Lodging"),
    ("25 hours", "Travel", "Hotels & Lodging"),
    ("w budapest", "Travel", "Hotels & Lodging"),
    ("therme", "Travel", "Attractions"),
    # Events / entertainment
    ("viagogo", "Entertainment", "Events & Tickets"),
    ("prudential center", "Entertainment", "Events & Tickets"),
    # Shopping
    ("mcshark", "Shopping", "Electronics"),
    ("klangfarbe", "Shopping", "Electronics"),
    ("swarovski", "Shopping", "General"),
    ("kadewe", "Shopping", "General"),
    ("blumen", "Shopping", "General"),
    ("action", "Shopping", "General"),
    # Health
    ("notino", "Health & Fitness", "Drugstore & Pharmacy"),
    ("fielmann", "Health & Fitness", "Healthcare"),
    # Connectivity
    ("saily", "Bills & Utilities", "Phone & Internet"),
    # --- More easy assignments from observed statements --------------------
    # Supermarkets / groceries
    ("rewe", "Food & Drink", "Groceries"),
    ("penny", "Food & Drink", "Groceries"),
    ("trafik", "Food & Drink", "Groceries"),
    ("chocolat", "Food & Drink", "Groceries"),
    # Cafés / restaurants (spellings the existing rules miss)
    ("caffe", "Food & Drink", "Restaurants & Cafés"),
    ("kaffee", "Food & Drink", "Restaurants & Cafés"),
    ("pizzeria", "Food & Drink", "Fast Food"),
    ("schnitzel", "Food & Drink", "Restaurants & Cafés"),
    ("plachutta", "Food & Drink", "Restaurants & Cafés"),
    # Drugstore / pharmacy / health
    ("rossmann", "Health & Fitness", "Drugstore & Pharmacy"),
    ("mueller wien", "Health & Fitness", "Drugstore & Pharmacy"),
    ("pearle", "Health & Fitness", "Healthcare"),
    ("whoop", "Health & Fitness", "Sports & Recreation"),
    # Transport
    ("united airlines", "Transport", "Flights"),
    ("garage", "Transport", "Parking"),
    ("matrica", "Transport", "Tolls"),
    ("mol ", "Transport", "Fuel"),
    ("oeamtc", "Transport", "Car Wash & Maintenance"),
    ("öamtc", "Transport", "Car Wash & Maintenance"),
    # Phone & internet
    ("t mobile", "Bills & Utilities", "Phone & Internet"),
    ("postpaid", "Bills & Utilities", "Phone & Internet"),
    # Shopping
    ("nkd", "Shopping", "Clothing"),
    # Entertainment / events
    ("stadthalle", "Entertainment", "Events & Tickets"),
    # --- Named food spots (observed restaurants / snack bars) --------------
    # NB: no bare "king" rule on purpose — it would match "parking"/"booking".
    # "Noodle king" is covered by the "noodle" pattern below.
    ("goldies", "Food & Drink", "Fast Food"),
    ("damak", "Food & Drink", "Fast Food"),
    ("turkis", "Food & Drink", "Fast Food"),
    ("noodle", "Food & Drink", "Restaurants & Cafés"),
    ("rinderwahn", "Food & Drink", "Restaurants & Cafés"),
    ("saloon", "Food & Drink", "Restaurants & Cafés"),
    # --- High-confidence well-known brands ---------------------------------
    # Supermarkets / convenience
    ("carrefour", "Food & Drink", "Groceries"),
    ("edeka", "Food & Drink", "Groceries"),
    ("wundermart", "Food & Drink", "Groceries"),
    # Fast food chains
    ("shake shack", "Food & Drink", "Fast Food"),
    ("in n out", "Food & Drink", "Fast Food"),
    ("burgerista", "Food & Drink", "Fast Food"),
    # Café / bakery chains
    ("le pain quotidien", "Food & Drink", "Restaurants & Cafés"),
    # Drugstore / pharmacy
    ("duane reade", "Health & Fitness", "Drugstore & Pharmacy"),
    # Retail
    ("media markt", "Shopping", "Electronics"),
    ("massimo dutti", "Shopping", "Clothing"),
    ("vinted", "Shopping", "Clothing"),
    ("ebay", "Shopping", "Online Shopping"),
    ("miniso", "Shopping", "General"),
    ("tedi", "Shopping", "General"),
    # Parking operators
    ("wipark", "Transport", "Parking"),
    ("contipark", "Transport", "Parking"),
    ("apcoa", "Transport", "Parking"),
    # Fuel
    ("enoc", "Transport", "Fuel"),
    # Trains
    ("db reisezentrum", "Transport", "Trains"),
    # Hotels / travel
    ("booking", "Travel", "Hotels & Lodging"),
    ("hyatt", "Travel", "Hotels & Lodging"),
    ("arlo soho", "Travel", "Hotels & Lodging"),
    # Travel eSIM / connectivity
    ("holafly", "Bills & Utilities", "Phone & Internet"),
]
