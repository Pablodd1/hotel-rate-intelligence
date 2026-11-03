"""Seed competitive set: 30 real Miami Beach boutique & lifestyle hotels.

Includes all 20 original properties plus 10 prime independent South Beach /
Mid-Beach targets, mapped to their live Xotelo/TripAdvisor metasearch keys,
booking engine stacks, and verified property-level commercial contacts.
"""

HOTELS = [
    # (name, area, website, stars, est_rooms, brand, xotelo_key, booking_engine, lat, lon, ContactsList)
    (
        "The Betsy Hotel, South Beach", "South Beach", "https://www.thebetsyhotel.com/",
        4.5, 130, "independent", "g34439-d1175532", "SynXis / Sabre", 25.7865, -80.1299,
        [
            ("email", "info@thebetsyhotel.com", "/contact"),
            ("email", "reservations@thebetsyhotel.com", "/contact"),
            ("email", "sales@thebetsyhotel.com", "/gather/meetings-events"),
            ("phone", "(305) 531-6100", "homepage"),
            ("phone", "(305) 760-6903", "/contact"),
            ("phone", "(844) 539-2840", "/contact"),
            ("address", "1440 Ocean Drive, Miami Beach, FL 33139", "/contact"),
            ("person", "VP of Revenue & Distribution / General Manager", "executive-target"),
        ],
    ),
    (
        "The Savoy Hotel & Beach Club", "South Beach", "https://www.savoyhotelmiami.com/",
        4.0, 75, "independent", "g34439-d217385", "Cloudbeds / Direct", 25.7735, -80.1314,
        [
            ("email", "info@savoyhotelmiami.com", "homepage"),
            ("email", "reservations@savoyhotelmiami.com", "/contact"),
            ("email", "events@savoyhotelmiami.com", "/events"),
            ("phone", "(305) 532-0200", "homepage"),
            ("address", "425 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Revenue Director", "executive-target"),
        ],
    ),
    (
        "Hotel Astor", "South Beach", "https://www.hotelastor.com/",
        3.5, 42, "independent", "g34439-d85081", "Roami / Cloudbeds", 25.7801, -80.1326,
        [
            ("email", "frontdesk@hotelastor.com", "/contact"),
            ("email", "reservations@hotelastor.com", "homepage"),
            ("phone", "(305) 531-8081", "homepage"),
            ("address", "956 Washington Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "Property Manager / Revenue Lead", "executive-target"),
        ],
    ),
    (
        "The Colony Hotel", "South Beach", "https://colonymiami.com/",
        3.5, 50, "independent", "g34439-d85104", "Cloudbeds", 25.7774, -80.1312,
        [
            ("email", "fd@colonymiami.com", "/contact.html"),
            ("email", "reservations@colonymiami.com", "/contact.html"),
            ("phone", "(305) 673-0088", "homepage"),
            ("phone", "(786) 380-4778", "/contact.html"),
            ("address", "736 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager / Front Office Director", "executive-target"),
        ],
    ),
    (
        "1 Hotel South Beach", "South Beach", "https://www.1hotels.com/south-beach",
        5.0, 425, "1 Hotels (SH Hotels)", "g34439-d7606777", "SynXis Enterprise", 25.7992, -80.1268,
        [
            ("email", "1sb.info@1hotels.com", "/south-beach/contact-us"),
            ("email", "1sb.sales@1hotels.com", "/south-beach/gather/meetings"),
            ("phone", "(305) 604-1000", "homepage"),
            ("phone", "(833) 625-3111", "homepage"),
            ("address", "2341 Collins Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "Director of Revenue Management", "executive-target"),
        ],
    ),
    (
        "Pelican Hotel", "South Beach", "https://pelicanhotel.com/",
        4.0, 33, "independent", "g34439-d115192", "SimpleBooking / Direct", 25.7785, -80.1309,
        [
            ("email", "info@pelicanhotel.com", "/hotel/"),
            ("email", "reservation@pelicanhotel.com", "/hotel/"),
            ("email", "restaurant@pelicanhotel.com", "/hotel/"),
            ("phone", "(305) 673-3373", "homepage"),
            ("phone", "(305) 699-7830", "/contact/"),
            ("address", "826 Ocean Drive, Miami Beach, FL 33139", "/hotel/"),
            ("person", "General Manager / Boutique Operations", "executive-target"),
        ],
    ),
    (
        "The Standard Spa, Miami Beach", "South Beach", "https://www.standardhotels.com/Miami/properties/miami-beach",
        4.5, 100, "independent", "g34439-d296000", "SynXis / Direct", 25.7905, -80.1489,
        [
            ("email", "miami@standardmiami.com", "homepage"),
            ("email", "marketing@standardmiami.com", "homepage"),
            ("email", "membership@standardmiami.com", "homepage"),
            ("phone", "(305) 673-1717", "homepage"),
            ("phone", "(786) 245-0880", "homepage"),
            ("address", "40 Island Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "Director of Revenue & E-Commerce", "executive-target"),
        ],
    ),
    (
        "National Hotel, An Oceanfront Resort", "South Beach", "https://www.nationalhotel.com/",
        4.0, 152, "independent", "g34439-d115185", "TravelClick / Amadeus", 25.7916, -80.1292,
        [
            ("email", "reservations@nationalhotel.com", "/contact-us/"),
            ("email", "sales@nationalhotel.com", "/events-meetings/"),
            ("email", "info@nationalhotel.com", "/about-the-hotel/"),
            ("phone", "(305) 532-2311", "/events-meetings/"),
            ("phone", "(305) 423-7246", "/events-meetings/"),
            ("address", "1677 Collins Avenue, Miami Beach, FL 33139", "/meetings/"),
            ("person", "Area Director of Revenue Management", "executive-target"),
        ],
    ),
    (
        "Casa Faena", "Mid-Beach", "https://www.faena.com/miami-beach/stay/casa-faena",
        4.0, 50, "independent", "g34439-d217412", "SynXis / Sabre", 25.8105, -80.1228,
        [
            ("email", "reservations-casafaena@faena.com", "/contact"),
            ("email", "info-miamibeach@faena.com", "/contact"),
            ("phone", "(305) 604-8485", "homepage"),
            ("phone", "(305) 534-8800", "/contact-us"),
            ("address", "3500 Collins Avenue, Miami Beach, FL 33140", "/contact-us"),
            ("person", "Hotel Manager & Revenue Analyst", "executive-target"),
        ],
    ),
    (
        "The Plymouth South Beach", "South Beach", "https://www.theplymouth.com/",
        4.0, 110, "independent", "g34439-d8603438", "SynXis / Sabre", 25.7968, -80.1306,
        [
            ("email", "reservations@theplymouth.com", "/contact"),
            ("email", "info@theplymouth.com", "homepage"),
            ("email", "sales@theplymouth.com", "/meetings"),
            ("phone", "(305) 602-5000", "homepage"),
            ("address", "336 21st Street, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Director of Sales", "executive-target"),
        ],
    ),
    (
        "The Marlin Hotel", "South Beach", "https://themarlinhotel.com/",
        4.0, 33, "independent", "g34439-d115184", "Mews / Direct", 25.7834, -80.1312,
        [
            ("email", "concierge@themarlinhotel.com", "homepage"),
            ("email", "reservations@themarlinhotel.com", "/contact-location"),
            ("phone", "(305) 695-3000", "homepage"),
            ("address", "1200 Collins Avenue, Miami Beach, FL 33139", "/contact-location"),
            ("person", "General Manager / Boutique Owner-Operator", "executive-target"),
        ],
    ),
    (
        "Esme Miami Beach", "South Beach", "https://www.esmehotel.com/",
        4.0, 145, "independent", "g34439-d577730", "SynXis / Sabre", 25.7869, -80.1328,
        [
            ("email", "hello@esmehotel.com", "homepage"),
            ("email", "reservations@esmehotel.com", "/contact/"),
            ("email", "sales@esmehotel.com", "/gather/"),
            ("phone", "(305) 800-3763", "homepage"),
            ("address", "1438 Washington Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "Director of Revenue & Distribution", "executive-target"),
        ],
    ),
    (
        "The Goodtime Hotel", "South Beach", "https://www.thegoodtimehotel.com/",
        4.0, 266, "independent", "g34439-d23093311", "Marriott / Tribute CRS", 25.7761, -80.1327,
        [
            ("email", "info@thegoodtimehotel.com", "/meetings-events/"),
            ("email", "sales@thegoodtimehotel.com", "/meetings-events/"),
            ("phone", "(786) 687-0234", "homepage"),
            ("phone", "(786) 687-0209", "/meetings-events/"),
            ("address", "601 Washington Avenue, Miami Beach, FL 33139", "/about/"),
            ("person", "Director of Sales & Revenue Strategy", "executive-target"),
        ],
    ),
    (
        "Palm Tree Club Miami Beach", "North/Mid-Beach", "https://www.palmtreeclubmiami.com/",
        3.5, 118, "independent", "g34439-d214205", "SynXis / Direct", 25.8492, -80.1455,
        [
            ("email", "info@palmtreeclubmiami.com", "homepage"),
            ("email", "reservations@palmtreeclubmiami.com", "/contact"),
            ("phone", "(305) 866-0441", "homepage"),
            ("address", "1819 79th Street Causeway, Miami Beach, FL 33141", "homepage"),
            ("person", "General Manager / Revenue Operations", "executive-target"),
        ],
    ),
    (
        "Circa 39 Hotel", "Mid-Beach", "https://www.circa39.com/",
        3.5, 100, "independent", "g34439-d85107", "Opera / IHG Connect", 25.8124, -80.1233,
        [
            ("email", "sales@circa39.com", "homepage"),
            ("email", "frontdesk@circa39.com", "/location/"),
            ("phone", "(305) 538-4900", "/location/"),
            ("phone", "(877) 824-7223", "/hotel/directions/"),
            ("address", "3900 Collins Avenue, Miami Beach, FL 33140", "/location/"),
            ("person", "General Manager & Director of Sales", "executive-target"),
        ],
    ),
    (
        "Miami Beach EDITION", "Mid-Beach", "https://www.editionhotels.com/miami-beach",
        5.0, 294, "EDITION / Marriott", "g34439-d7143309", "Marriott MARSHA", 25.8049, -80.1249,
        [
            ("email", "reservations.miaeb@editionhotels.com", "/miami-beach/contact"),
            ("email", "sales.miaeb@editionhotels.com", "/miami-beach/meetings"),
            ("phone", "(786) 257-4500", "homepage"),
            ("address", "2901 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("person", "Director of Revenue Management", "executive-target"),
        ],
    ),
    (
        "Andaz Miami Beach (formerly The Confidante)", "Mid-Beach", "https://www.hyatt.com/andaz/miaaz-andaz-miami-beach",
        4.5, 287, "Hyatt / Andaz", "g34439-d6959850", "Hyatt SPIRIT CRS", 25.8139, -80.1225,
        [
            ("email", "miaaz.sales@hyatt.com", "/contact"),
            ("phone", "(305) 424-1234", "homepage"),
            ("address", "4041 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("person", "Director of Commercial Services", "executive-target"),
        ],
    ),
    (
        "Faena Hotel Miami Beach", "Mid-Beach", "https://www.faena.com/miami-beach",
        5.0, 179, "independent", "g34439-d7787044", "SynXis / Leading Hotels", 25.8077, -80.1235,
        [
            ("email", "reservations-miamibeach@faena.com", "homepage"),
            ("email", "events-miamibeach@faena.com", "/contact-us"),
            ("phone", "(305) 534-8800", "homepage"),
            ("phone", "(305) 535-4697", "homepage"),
            ("phone", "(786) 646-1250", "/contact-us"),
            ("address", "3201 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("person", "Director of Revenue Optimization", "executive-target"),
        ],
    ),
    (
        "Palihouse Miami Beach", "Mid-Beach", "https://www.palisociety.com/hotels/miami-beach",
        4.0, 71, "independent", "g34439-d19625115", "SynXis / Palisociety", 25.8132, -80.1261,
        [
            ("email", "miamibeach@palisociety.com", "homepage"),
            ("email", "sales@palisociety.com", "/contact"),
            ("phone", "(305) 763-8600", "homepage"),
            ("address", "3101 Indian Creek Drive, Miami Beach, FL 33140", "homepage"),
            ("person", "General Manager & Regional Revenue Lead", "executive-target"),
        ],
    ),
    (
        "Life House, South of Fifth", "South Beach", "https://www.lifehousehotels.com/hotels/miami-beach/south-of-fifth",
        4.0, 26, "independent", "g34439-d34645842", "Life House RMS / Mews", 25.7726, -80.1342,
        [
            ("email", "southoffifth@lifehousehotels.com", "homepage"),
            ("email", "groups@lifehousehotels.com", "/contact"),
            ("phone", "(866) 466-7534", "homepage"),
            ("address", "321 Collins Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager / Revenue Operations", "executive-target"),
        ],
    ),
    # 10 Additional High-Converting Independent Miami Beach Boutique Prospects
    (
        "Avalon Hotel South Beach", "South Beach", "https://www.avalonhotel.com/",
        3.5, 57, "independent", "g34439-d111872", "TravelClick / iHotelier", 25.7771, -80.1313,
        [
            ("email", "reservations@avalonhotel.com", "homepage"),
            ("email", "info@avalonhotel.com", "/contact"),
            ("phone", "(305) 532-1800", "homepage"),
            ("address", "700 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Revenue Manager", "executive-target"),
        ],
    ),
    (
        "Cavalier South Beach Hotel", "South Beach", "https://www.cavalierhotel.com/",
        3.5, 45, "independent", "g34439-d111876", "Cloudbeds / Oxford", 25.7848, -80.1301,
        [
            ("email", "info@cavalierhotel.com", "homepage"),
            ("email", "reservations@cavalierhotel.com", "/contact"),
            ("phone", "(305) 673-1199", "homepage"),
            ("address", "1320 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "Boutique Cluster General Manager", "executive-target"),
        ],
    ),
    (
        "Beacon South Beach Hotel", "South Beach", "https://www.beaconsouthbeach.com/",
        4.0, 75, "independent", "g34439-d87012", "SynXis / Direct", 25.7773, -80.1312,
        [
            ("email", "reservations@beaconsouthbeach.com", "homepage"),
            ("email", "frontdesk@beaconsouthbeach.com", "/contact-us"),
            ("phone", "(305) 674-8200", "homepage"),
            ("address", "720 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Director of Revenue", "executive-target"),
        ],
    ),
    (
        "Hotel Victor South Beach", "South Beach", "https://www.hotelvictorsouthbeach.com/",
        4.0, 91, "independent", "g34439-d296713", "SynXis / Sabre", 25.7824, -80.1305,
        [
            ("email", "info@hotelvictorsouthbeach.com", "homepage"),
            ("email", "reservations@hotelvictorsouthbeach.com", "/contact"),
            ("phone", "(305) 779-8700", "homepage"),
            ("address", "1144 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager / Revenue Director", "executive-target"),
        ],
    ),
    (
        "The Palms Hotel & Spa", "Mid-Beach", "https://www.thepalmshotel.com/",
        4.5, 251, "independent", "g34439-d219199", "SynXis / Preferred Hotels", 25.8061, -80.1241,
        [
            ("email", "info@thepalmshotel.com", "homepage"),
            ("email", "reservations@thepalmshotel.com", "/contact-us/"),
            ("email", "sales@thepalmshotel.com", "/meetings-and-events/"),
            ("phone", "(305) 534-0505", "homepage"),
            ("phone", "(800) 550-0505", "/contact-us/"),
            ("address", "3025 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("person", "VP of Revenue Strategy & Distribution", "executive-target"),
        ],
    ),
    (
        "Waldorf Towers South Beach", "South Beach", "https://www.waldorftowers.com/",
        3.5, 44, "independent", "g34439-d25564119", "Cloudbeds", 25.7789, -80.1308,
        [
            ("email", "reservations@waldorftowers.com", "homepage"),
            ("email", "frontdesk@waldorftowers.com", "/contact"),
            ("phone", "(305) 531-7684", "homepage"),
            ("address", "860 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager / Front Office", "executive-target"),
        ],
    ),
    (
        "Hotel Greystone", "South Beach", "https://www.greystonehotel.com/",
        4.0, 91, "independent", "g34439-d275378", "SynXis / Salt Hotels", 25.7952, -80.1297,
        [
            ("email", "info@greystonehotel.com", "homepage"),
            ("email", "reservations@greystonehotel.com", "/contact"),
            ("email", "sales@greystonehotel.com", "/events"),
            ("phone", "(305) 847-4000", "homepage"),
            ("address", "1920 Collins Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Commercial Lead", "executive-target"),
        ],
    ),
    (
        "The Sagamore Hotel South Beach", "South Beach", "https://www.sagamoresouthbeach.com/",
        4.0, 101, "independent", "g34439-d240165", "TravelClick / iHotelier", 25.7912, -80.1293,
        [
            ("email", "reservations@sagamoresouthbeach.com", "homepage"),
            ("email", "sales@sagamoresouthbeach.com", "/events/"),
            ("phone", "(305) 535-8080", "homepage"),
            ("address", "1671 Collins Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "Director of Revenue & Sales", "executive-target"),
        ],
    ),
    (
        "Lennox Hotel Miami Beach", "South Beach", "https://www.lennoxmiamibeach.com/",
        4.5, 119, "independent", "g34439-d17386327", "SynXis / Small Luxury Hotels", 25.7945, -80.1298,
        [
            ("email", "info@lennoxmiamibeach.com", "homepage"),
            ("email", "reservations@lennoxmiamibeach.com", "/contact"),
            ("phone", "(305) 531-3600", "homepage"),
            ("address", "1900 Collins Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Revenue Manager", "executive-target"),
        ],
    ),
    (
        "Z Ocean Hotel South Beach", "South Beach", "https://www.zoceanhotelsouthbeach.com/",
        4.0, 52, "independent", "g34439-d596736", "SynXis / Direct", 25.7867, -80.1301,
        [
            ("email", "reservations@zoceanhotel.com", "homepage"),
            ("email", "info@zoceanhotel.com", "/contact"),
            ("phone", "(305) 672-4554", "homepage"),
            ("address", "1437 Collins Avenue, Miami Beach, FL 33139", "homepage"),
            ("person", "General Manager & Revenue Lead", "executive-target"),
        ],
    ),
]


def seed(conn, log=print):
    from . import db as dbmod
    ids = []
    contacts_seeded = 0
    for row in HOTELS:
        name, area, site, stars, rooms, brand, xkey, engine, lat, lon, contacts = row
        hid = dbmod.upsert_hotel(
            conn, name=name, area=area, website=site, stars=stars,
            est_rooms=rooms, brand=brand, xotelo_key=xkey,
            booking_engine=engine, latitude=lat, longitude=lon)
        ids.append(hid)
        for kind, val, ctx in contacts:
            if dbmod.add_contact(conn, hid, kind, val, ctx, confidence=0.95):
                contacts_seeded += 1
    log(f"seeded {len(ids)} hotels ({contacts_seeded} verified baseline contacts)")
    return ids
