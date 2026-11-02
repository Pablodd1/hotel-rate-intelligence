"""Seed competitive set: 20 real Miami Beach boutique/independent hotels.

Names, neighborhoods and official websites are public knowledge; est_rooms and
stars are estimates to calibrate the prospect scoring — correct them as you
verify (PUT /api/hotels/<id>).
"""
HOTELS = [
    # name, area, website, stars, est_rooms
    ("The Betsy Hotel, South Beach", "South Beach", "https://thebetsyhotel.com/", 4.5, 130),
    ("The Savoy Hotel & Beach Club", "South Beach", "https://www.savoyhotel.com/", 4, 75),
    ("Hotel Astor", "South Beach", "https://www.hotelastor.com/", 3.5, 40),
    ("The Colony Hotel", "South Beach", "https://colonymiami.com/", 3, 50),
    ("1 Hotel South Beach", "South Beach", "https://www.1hotels.com/south-beach", 5, 425),
    ("Pelican Hotel", "South Beach", "https://pelicanhotel.com/", 3.5, 30),
    ("The Standard Spa, Miami Beach", "South Beach", "https://www.standardhotels.com/spa-miami-beach", 4.5, 100),
    ("National Hotel, An Oceanfront Resort", "South Beach", "https://www.nationalhotel.com/", 4, 150),
    ("Casa Faena", "Miami Beach", "https://casafaena.com/", 4, 50),
    ("The Plymouth South Beach", "South Beach", "https://theplymouth.com/", 4, 50),
    ("The Marlin Hotel", "South Beach", "https://themarlinhotel.com/", 4, 80),
    ("Esme Miami Beach", "South Beach", "https://hotelsme.com/", 4, 50),
    ("The Goodtime Hotel", "South Beach", "https://www.thegoodtimehotel.com/", 4, 266),
    ("Palm Tree Club Miami Beach", "Mid-Beach", "https://palmtreeclubmiamibeach.com/", 3.5, 80),
    ("Circa 39 Hotel", "Mid-Beach", "https://www.circa39.com/", 3.5, 100),
    ("Miami Beach EDITION", "Mid-Beach", "https://www.editionhotels.com/miami-beach", 5, 300),
    ("The Confidante Miami Beach", "Mid-Beach", "https://www.hyatt.com/the-confidante", 4, 350),
    ("Faena Hotel Miami Beach", "Mid-Beach", "https://www.faena.com/miami-beach", 5, 170),
    ("Palihouse Miami Beach", "Miami Beach", "https://www.palihouse.com/miami-beach", 4, 80),
    ("Life House, South of Fifth", "South Beach", "https://www.lifehousehotels.com/miami-beach", 3.5, 64),
]


def seed(conn, log=print):
    from . import db as dbmod
    ids = []
    for name, area, site, stars, rooms in HOTELS:
        ids.append(dbmod.upsert_hotel(conn, name=name, area=area, website=site,
                                      stars=stars, est_rooms=rooms))
    log(f"seeded {len(ids)} hotels ({len(set(ids))} new/known)")
    return ids
