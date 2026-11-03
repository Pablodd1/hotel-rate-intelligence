"""Seed competitive set: 42 real Greater Miami, North Beach, MiMo Biscayne & South Beach hotels.

Organized across 4 local corridors around North Miami / Miami Beach / Miami:
  1. North Beach & 79th St Causeway (60th–79th St — closest to North Miami)
  2. Miami Mainland — MiMo Biscayne Blvd (60th–75th St), Wynwood, Downtown & Grove
  3. Mid-Beach (29th–48th St Collins & Indian Creek)
  4. South Beach (3rd–23rd St Ocean Drive, Collins & Washington)
"""

HOTELS = [
    # ==================== CORRIDOR 1: NORTH BEACH & 79TH ST CAUSEWAY ====================
    (
        "Seaside All Suites Hotel", "North Beach", "https://www.seasideallsuiteshotel.com/",
        3.5, 45, "independent", "g34439-d7722355", "Cloudbeds / SBG", 25.8602, -80.1211,
        [
            ("email", "info@seasideallsuiteshotel.com", "homepage"),
            ("email", "reservations@sbghotels.com", "/contact"),
            ("phone", "(305) 866-7033", "homepage"),
            ("address", "7500 Collins Avenue, Miami Beach, FL 33141", "homepage"),
            ("instagram", "@sbghotels", "social"),
            ("person", "Property Manager / North Beach Operations", "executive-target"),
        ],
    ),
    (
        "Waterside Hotel & Suites", "North Beach", "https://www.watersidehotelmiamibeach.com/",
        3.5, 49, "independent", "g34439-d11740991", "Cloudbeds / Direct", 25.8584, -80.1228,
        [
            ("email", "frontdesk@watersidehotelmiamibeach.com", "homepage"),
            ("email", "reservations@watersidehotelmiamibeach.com", "/contact"),
            ("phone", "(305) 868-9626", "homepage"),
            ("address", "7310 Harding Avenue, Miami Beach, FL 33141", "homepage"),
            ("instagram", "@watersidehotelmiami", "social"),
            ("person", "Owner / General Manager", "executive-target"),
        ],
    ),
    (
        "Park Royal Miami Beach", "North Beach", "https://www.parkroyalmiamibeach.com/",
        3.5, 42, "independent", "g34439-d12189838", "SynXis / Direct", 25.8522, -80.1243,
        [
            ("email", "reservations@parkroyalmiamibeach.com", "homepage"),
            ("email", "frontdesk@parkroyalmiamibeach.com", "/contact"),
            ("phone", "(305) 866-4621", "homepage"),
            ("address", "6800 Indian Creek Drive, Miami Beach, FL 33141", "homepage"),
            ("instagram", "@parkroyalhotels", "social"),
            ("person", "General Manager & Front Office Lead", "executive-target"),
        ],
    ),
    (
        "Oceanside Hotel + Suites", "North Beach", "https://www.oceansidehotelmiami.com/",
        3.5, 100, "independent", "g34439-d10263831", "Mews / Direct", 25.8442, -80.1214,
        [
            ("email", "info@oceansidehotelmiami.com", "homepage"),
            ("email", "reservations@oceansidehotelmiami.com", "/contact"),
            ("phone", "(305) 763-8146", "homepage"),
            ("address", "6084 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("instagram", "@oceansidehotel", "social"),
            ("person", "General Manager & Revenue Manager", "executive-target"),
        ],
    ),
    (
        "Palm Tree Club Miami Beach", "North Beach", "https://www.palmtreeclubmiami.com/",
        3.5, 118, "independent", "g34439-d214205", "SynXis / Direct", 25.8492, -80.1455,
        [
            ("email", "info@palmtreeclubmiami.com", "homepage"),
            ("email", "reservations@palmtreeclubmiami.com", "/contact"),
            ("phone", "(305) 866-0441", "homepage"),
            ("address", "1819 79th Street Causeway, North Bay Village, FL 33141", "homepage"),
            ("instagram", "@palmtreeclubmiami", "social"),
            ("person", "General Manager / Revenue Operations", "executive-target"),
        ],
    ),
    (
        "Grand Beach Hotel Surfside / Miami Beach", "North Beach", "https://www.grandbeachhotel.com/",
        4.0, 268, "independent", "g34439-d1200086", "TravelClick / iHotelier", 25.8245, -80.1219,
        [
            ("email", "reservations@grandbeachhotel.com", "homepage"),
            ("email", "sales@grandbeachhotel.com", "/meetings"),
            ("phone", "(305) 538-8666", "homepage"),
            ("address", "4835 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("instagram", "@grandbeachhotel", "social"),
            ("person", "Director of Revenue Management", "executive-target"),
        ],
    ),

    # ==================== CORRIDOR 2: MIAMI MAINLAND (MIMO BISCAYNE, WYNWOOD, DOWNTOWN) ====================
    (
        "The Vagabond Hotel Miami (MiMo)", "Miami (MiMo / Biscayne)", "https://www.thevagabondhotelmiami.com/",
        4.0, 45, "independent", "g34438-d6727321", "Cloudbeds / Direct", 25.8421, -80.1841,
        [
            ("email", "info@thevagabondhotelmiami.com", "homepage"),
            ("email", "reservations@thevagabondhotelmiami.com", "/contact"),
            ("phone", "(305) 400-8420", "homepage"),
            ("address", "7301 Biscayne Boulevard, Miami, FL 33138", "homepage"),
            ("instagram", "@thevagabondhotel", "social"),
            ("person", "General Manager / Boutique Owner", "executive-target"),
        ],
    ),
    (
        "The New Yorker Boutique Hotel (MiMo)", "Miami (MiMo / Biscayne)", "https://www.newyorkermiami.com/",
        3.5, 30, "independent", "g34438-d1758216", "Cloudbeds / Direct", 25.8355, -80.1844,
        [
            ("email", "info@newyorkermiami.com", "homepage"),
            ("email", "frontdesk@newyorkermiami.com", "/contact"),
            ("phone", "(305) 759-5823", "homepage"),
            ("address", "6500 Biscayne Boulevard, Miami, FL 33138", "homepage"),
            ("instagram", "@newyorkerhotelmiami", "social"),
            ("person", "Owner-Operator & Front Desk Manager", "executive-target"),
        ],
    ),
    (
        "The Biscayne Hotel (MiMo)", "Miami (MiMo / Biscayne)", "https://www.thebiscaynehotel.com/",
        3.5, 32, "independent", "g34438-d26332658", "Little Hotelier / Direct", 25.8315, -80.1848,
        [
            ("email", "reservations@thebiscaynehotel.com", "homepage"),
            ("phone", "(305) 758-4522", "homepage"),
            ("address", "6060 Biscayne Boulevard, Miami, FL 33137", "homepage"),
            ("instagram", "@thebiscaynehotel", "social"),
            ("person", "Owner / Property Manager", "executive-target"),
        ],
    ),
    (
        "Arlo Wynwood Miami", "Miami (Wynwood / Downtown)", "https://www.arlohotels.com/arlo-wynwood/",
        4.5, 217, "independent", "g34438-d24889567", "SynXis / Arlo", 25.7985, -80.1972,
        [
            ("email", "wynwood@arlohotels.com", "homepage"),
            ("email", "sales@arlohotels.com", "/contact"),
            ("phone", "(786) 522-6600", "homepage"),
            ("address", "2217 NW Miami Court, Miami, FL 33127", "homepage"),
            ("instagram", "@arlowynwood", "social"),
            ("person", "Director of Revenue Strategy", "executive-target"),
        ],
    ),
    (
        "Eurostars Langford Downtown Miami", "Miami (Wynwood / Downtown)", "https://www.eurostarshotels.co.uk/eurostars-langford.html",
        4.0, 126, "independent", "g34438-d8778365", "Direct / Eurostars CRS", 25.7731, -80.1908,
        [
            ("email", "reservations@langfordhotelmiami.com", "homepage"),
            ("email", "info@langfordhotelmiami.com", "/contact"),
            ("phone", "(305) 420-2200", "homepage"),
            ("address", "121 SE 1st Street, Miami, FL 33131", "homepage"),
            ("instagram", "@eurostarslangford", "social"),
            ("person", "General Manager & Revenue Lead", "executive-target"),
        ],
    ),
    (
        "The Mutiny Luxury Suites Hotel", "Miami (Wynwood / Downtown)", "https://www.mutinyhotel.com/",
        4.0, 120, "independent", "g34438-d87137", "TravelClick / iHotelier", 25.7279, -80.2392,
        [
            ("email", "reservations@mutinyhotel.com", "homepage"),
            ("email", "sales@mutinyhotel.com", "/contact"),
            ("phone", "(305) 441-2100", "homepage"),
            ("address", "2951 S Bayshore Drive, Coconut Grove, Miami, FL 33133", "homepage"),
            ("instagram", "@themutinyhotel", "social"),
            ("person", "General Manager & Director of Revenue", "executive-target"),
        ],
    ),

    # ==================== CORRIDOR 3: MID-BEACH (29TH–41ST ST) ====================
    (
        "Circa 39 Hotel", "Mid-Beach", "https://www.circa39.com/",
        3.5, 100, "independent", "g34439-d85107", "Opera / IHG Connect", 25.8124, -80.1233,
        [
            ("email", "sales@circa39.com", "homepage"),
            ("email", "frontdesk@circa39.com", "/location/"),
            ("phone", "(305) 538-4900", "/location/"),
            ("phone", "(877) 824-7223", "/hotel/directions/"),
            ("address", "3900 Collins Avenue, Miami Beach, FL 33140", "/location/"),
            ("instagram", "@circa39hotel", "social"),
            ("person", "General Manager & Director of Sales", "executive-target"),
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
            ("instagram", "@palisociety", "social"),
            ("person", "General Manager & Regional Revenue Lead", "executive-target"),
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
            ("instagram", "@casafaena", "social"),
            ("person", "Hotel Manager & Revenue Analyst", "executive-target"),
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
            ("instagram", "@thepalmshotel", "social"),
            ("person", "VP of Revenue Strategy & Distribution", "executive-target"),
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
            ("address", "3201 Collins Avenue, Miami Beach, FL 33140", "homepage"),
            ("instagram", "@faena", "social"),
            ("person", "Director of Revenue Optimization", "executive-target"),
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
            ("instagram", "@miamibeachedition", "social"),
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
            ("instagram", "@andazmiamibeach", "social"),
            ("person", "Director of Commercial Services", "executive-target"),
        ],
    ),

    # ==================== CORRIDOR 4: SOUTH BEACH (OCEAN DR, COLLINS, WASHINGTON) ====================
    (
        "The Colony Hotel", "South Beach", "https://colonymiami.com/",
        3.5, 50, "independent", "g34439-d85104", "Cloudbeds", 25.7774, -80.1312,
        [
            ("email", "fd@colonymiami.com", "/contact.html"),
            ("email", "reservations@colonymiami.com", "/contact.html"),
            ("phone", "(305) 673-0088", "homepage"),
            ("phone", "(786) 380-4778", "/contact.html"),
            ("address", "736 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("instagram", "@colonymiami", "social"),
            ("person", "General Manager / Front Office Director", "executive-target"),
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
            ("instagram", "@pelicanhotelmiami", "social"),
            ("person", "General Manager / Boutique Operations", "executive-target"),
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
            ("instagram", "@hotelastormiami", "social"),
            ("person", "Property Manager / Revenue Lead", "executive-target"),
        ],
    ),
    (
        "Avalon Hotel South Beach", "South Beach", "https://www.avalonhotel.com/",
        3.5, 57, "independent", "g34439-d111872", "TravelClick / iHotelier", 25.7771, -80.1313,
        [
            ("email", "reservations@avalonhotel.com", "homepage"),
            ("email", "info@avalonhotel.com", "/contact"),
            ("phone", "(305) 532-1800", "homepage"),
            ("address", "700 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("instagram", "@avalonhotelsouthbeach", "social"),
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
            ("instagram", "@cavaliersouthbeach", "social"),
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
            ("instagram", "@beaconsouthbeach", "social"),
            ("person", "General Manager & Director of Revenue", "executive-target"),
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
            ("instagram", "@waldorftowers", "social"),
            ("person", "General Manager / Front Office", "executive-target"),
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
            ("instagram", "@themarlinhotel", "social"),
            ("person", "General Manager / Boutique Owner-Operator", "executive-target"),
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
            ("instagram", "@zoceanhotel", "social"),
            ("person", "General Manager & Revenue Lead", "executive-target"),
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
            ("instagram", "@lifehousehotels", "social"),
            ("person", "General Manager / Revenue Operations", "executive-target"),
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
            ("instagram", "@savoyhotelmiami", "social"),
            ("person", "General Manager & Revenue Director", "executive-target"),
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
            ("instagram", "@hotelvictorsobe", "social"),
            ("person", "General Manager / Revenue Director", "executive-target"),
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
            ("instagram", "@hotelgreystone", "social"),
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
            ("instagram", "@sagamorehotel", "social"),
            ("person", "Director of Revenue & Sales", "executive-target"),
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
            ("instagram", "@theplymouthmiami", "social"),
            ("person", "General Manager & Director of Sales", "executive-target"),
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
            ("instagram", "@lennoxmiamibeach", "social"),
            ("person", "General Manager & Revenue Manager", "executive-target"),
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
            ("instagram", "@esmehotel", "social"),
            ("person", "Director of Revenue & Distribution", "executive-target"),
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
            ("instagram", "@thestandardmiami", "social"),
            ("person", "Director of Revenue & E-Commerce", "executive-target"),
        ],
    ),
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
            ("instagram", "@thebetsyhotel", "social"),
            ("person", "VP of Revenue & Distribution / General Manager", "executive-target"),
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
            ("instagram", "@nationalhotelmiami", "social"),
            ("person", "Area Director of Revenue Management", "executive-target"),
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
            ("instagram", "@thegoodtimehotel", "social"),
            ("person", "Director of Sales & Revenue Strategy", "executive-target"),
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
            ("instagram", "@1hotels", "social"),
            ("person", "Director of Revenue Management", "executive-target"),
        ],
    ),
    (
        "Clevelander South Beach Hotel", "South Beach", "https://www.clevelander.com/",
        3.5, 60, "independent", "g34439-d85102", "SynXis / Direct", 25.7808, -80.1306,
        [
            ("email", "reservations@clevelander.com", "homepage"),
            ("email", "info@clevelander.com", "/contact"),
            ("phone", "(305) 532-4006", "homepage"),
            ("address", "1020 Ocean Drive, Miami Beach, FL 33139", "homepage"),
            ("instagram", "@clevelandersobe", "social"),
            ("person", "General Manager & Hotel Revenue Lead", "executive-target"),
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
