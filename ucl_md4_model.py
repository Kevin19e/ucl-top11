"""UCL 2026/27 Matchday 4 (3-4 Nov 2026): P(goal or assist) per player.

Same method and constants as ucl_md2_model.py; only the inputs are new. Collected on 2026-10-26 from:
  - Understat league pages (2026/27 to date and 2025/26 full season): minutes, goals,
    assists, xG, xA, npxG. Domestic league only (top-5 leagues).
  - Team news: sportsgambler.com injury and suspension list (26 Oct 2026) plus club and press reports.
    UEFA.com's predicted line-ups article for Matchday 4 was not out yet, so start chances are estimates.
  - Bookmaker 1X2 prices (oddschecker best prices, 26 Oct 2026). Each team's match xG is the
    Poisson fit to the home and away win probabilities (totals prices were not collected).
START, PEN_SHARE are analyst judgements, not measured data.
"""
import math

K_MIN = 900            # shrinkage pseudo-minutes toward the position prior
PREV_W = 0.5           # weight of last season's minutes
FINISH_C = 20          # pseudo-goals for the light "actual goals/assists" blend
PEN_PER_XG = 0.095     # expected penalties awarded per team expected goal
PEN_CONV = 0.78
SUB_MIN = 14           # expected minutes when not starting (0.7 * 20)
BAND = 0.20            # heuristic +/- on lambda for the uncertainty range
WIDE_BAND = 0.30       # same, for players with a role change or a real start doubt
WIDE = {"Raphinha", "Florian Wirtz", "Dominik Szoboszlai", "Pau Cubarsí", "Ismael Saibari", "Viktor Gyökeres",
        "Eberechi Eze", "Noni Madueke", "Isco", "Serge Gnabry", "Lennart Karl", "Daniel Svensson", "Dean Huijsen",
        "Kai Havertz", "Deniz Undav"}

# Players who changed club: last season's numbers were produced in a different attack.
# Value = previous club's league xG per game; last-season stats are rescaled by
# clip(current team baseline / previous, 0.75, 1.33).
PREV_TEAM_XG = {
    "Nicolas Jackson": 3.08, "Christopher Nkunku": 1.71, "Jonathan David": 1.95, "Anthony Gordon": 1.59,
    "Karim Adeyemi": 1.99, "Ferran Torres": 2.62, "Álex Grimaldo": 2.21, "Ezri Konsa": 1.48, "Marc Cucurella": 1.90,
    "Bradley Barcola": 2.22, "Ronald Araújo": 2.62, "Ibrahima Konaté": 1.77, "Denzel Dumfries": 2.29,
    "Yan Diomande": 2.21, "Maghnes Akliouche": 1.81, "Iliman Ndiaye": 1.31, "Jérémy Jacquet": 1.60, "Marc Guéhi": 1.64,
}

# position prior per 90: (npxG, xA)
PRIOR = {"ST": (0.40, 0.12), "W": (0.25, 0.20), "CM": (0.10, 0.12), "WB": (0.06, 0.12),
         "FB": (0.04, 0.10), "CB": (0.05, 0.02)}
MIN_IF_START = {"ST": 76, "W": 74, "CM": 80, "WB": 84, "FB": 84, "CB": 88}

# team: (opponent, H/A, match xG assumption, xG 26/27, games 26/27, xG 25/26, games 25/26)
TEAMS = {
    "Stuttgart": ("Galatasaray", "A", 1.42, 15.31, 7, 68.3, 34),
    "Atlético": ("Bayern", "H", 1.23, 19.69, 10, 68.1, 38),
    "Bayern": ("Atlético", "A", 1.65, 25.90, 7, 104.8, 34),
    "Barcelona": ("Aston Villa", "H", 2.97, 37.15, 10, 99.7, 38),
    "Aston Villa": ("Barcelona", "A", 0.95, 9.56, 8, 56.2, 38),
    "Lille": ("Bodø/Glimt", "A", 1.12, 11.38, 8, 57.2, 34),
    "Inter": ("Feyenoord", "A", 1.91, 24.81, 8, 87.1, 38),
    "Man United": ("Roma", "H", 1.55, 13.38, 8, 72.2, 38),
    "Roma": ("Man United", "A", 1.31, 20.61, 8, 62.6, 38),
    "Villarreal": ("Paris SG", "H", 1.14, 23.94, 10, 68.8, 38),
    "Paris SG": ("Villarreal", "A", 2.03, 18.03, 7, 75.6, 34),
    "Real Madrid": ("AEK Athens", "A", 2.50, 25.16, 10, 81.5, 38),
    "Liverpool": ("Fenerbahçe", "A", 1.90, 11.83, 8, 67.3, 38),
    "Dortmund": ("Real Betis", "H", 1.69, 13.92, 7, 67.8, 34),
    "Real Betis": ("Dortmund", "A", 1.00, 18.24, 10, 61.3, 38),
    "Napoli": ("Porto", "A", 1.08, 17.95, 8, 57.8, 38),
    "Lens": ("Como", "H", 1.35, 16.46, 8, 74.4, 34),
    "Como": ("Lens", "A", 1.60, 17.83, 8, 68.0, 38),
    "Leipzig": ("Man City", "H", 1.01, 17.22, 7, 75.2, 34),
    "Man City": ("Leipzig", "A", 2.06, 18.92, 8, 79.4, 38),
    "Arsenal": ("Slavia Praha", "A", 2.35, 14.93, 8, 77.5, 38),
}

# name, team, pos, P(start), pen share,
#   26/27: min, G, A, xG, xA, npxG | 25/26: min, G, A, xG, xA, npxG
P = [
 ("Harry Kane", "Bayern", "ST", 0.90, 0.95, 537, 4, 5, 5.96, 3.22, 5.20, 2385, 36, 5, 29.58, 7.40, 21.24),
 ("Michael Olise", "Bayern", "W", 0.85, 0.05, 571, 6, 3, 3.98, 3.69, 3.98, 2308, 15, 19, 11.55, 17.04, 11.55),
 ("Ismael Saibari", "Bayern", "W", 0.75, 0.00, 339, 2, 2, 3.94, 1.69, 3.94, 0, 0, 0, 0.00, 0.00, 0.00),
 ("Serge Gnabry", "Bayern", "W", 0.55, 0.00, 124, 1, 0, 2.07, 0.52, 2.07, 1280, 8, 6, 6.26, 5.15, 6.26),
 ("Lennart Karl", "Bayern", "W", 0.45, 0.00, 254, 1, 0, 0.70, 0.33, 0.70, 1268, 5, 5, 7.12, 2.79, 7.12),
 ("Lamine Yamal", "Barcelona", "W", 0.90, 0.40, 849, 8, 6, 7.27, 5.57, 5.78, 2291, 16, 11, 14.66, 12.57, 11.69),
 ("Raphinha", "Barcelona", "W", 0.80, 0.55, 678, 13, 3, 9.55, 2.87, 7.32, 1424, 13, 3, 11.13, 5.91, 8.90),
 ("Fermín López", "Barcelona", "W", 0.65, 0.00, 624, 4, 3, 3.05, 3.00, 3.05, 1780, 6, 9, 7.52, 7.65, 7.52),
 ("Anthony Gordon", "Barcelona", "W", 0.50, 0.00, 600, 1, 4, 3.26, 2.10, 3.26, 1888, 6, 2, 8.76, 3.71, 6.47),
 ("Karim Adeyemi", "Barcelona", "W", 0.30, 0.00, 309, 2, 2, 4.29, 1.54, 4.29, 1218, 7, 4, 5.22, 3.46, 5.22),
 ("Pedri", "Barcelona", "CM", 0.85, 0.00, 737, 1, 2, 0.62, 1.69, 0.62, 2117, 2, 9, 2.39, 5.95, 2.39),
 ("Martin Ødegaard", "Arsenal", "W", 0.80, 0.35, 661, 2, 0, 2.15, 2.12, 2.15, 1347, 1, 6, 1.22, 4.98, 1.22),
 ("Kai Havertz", "Arsenal", "ST", 0.70, 0.35, 598, 2, 0, 1.72, 0.39, 1.72, 582, 2, 3, 4.90, 1.46, 4.90),
 ("Viktor Gyökeres", "Arsenal", "ST", 0.40, 0.20, 138, 0, 1, 0.05, 1.63, 0.05, 2255, 14, 1, 13.87, 2.65, 11.59),
 ("Noni Madueke", "Arsenal", "W", 0.65, 0.00, 241, 1, 0, 0.45, 0.87, 0.45, 1246, 2, 1, 2.00, 4.01, 2.00),
 ("Eberechi Eze", "Arsenal", "W", 0.60, 0.00, 211, 0, 0, 0.11, 0.03, 0.11, 1928, 7, 2, 4.81, 2.63, 4.81),
 ("Declan Rice", "Arsenal", "CM", 0.90, 0.00, 680, 0, 4, 0.23, 1.33, 0.23, 3111, 4, 5, 3.72, 8.16, 3.72),
 ("Marcus Thuram", "Inter", "ST", 0.85, 0.10, 458, 5, 2, 5.01, 1.08, 5.01, 1933, 13, 6, 11.90, 4.47, 11.90),
 ("Francesco Pio Esposito", "Inter", "ST", 0.70, 0.00, 485, 2, 1, 3.05, 0.69, 3.05, 1535, 7, 3, 9.86, 2.06, 9.86),
 ("Hakan Çalhanoğlu", "Inter", "CM", 0.75, 0.85, 286, 3, 0, 0.94, 1.08, 0.18, 1674, 9, 4, 5.15, 3.48, 1.34),
 ("Nicolò Barella", "Inter", "CM", 0.85, 0.00, 625, 1, 2, 0.86, 2.41, 0.86, 2561, 3, 8, 3.82, 7.97, 3.82),
 ("Piotr Zieliński", "Inter", "CM", 0.50, 0.05, 449, 2, 2, 1.46, 1.62, 0.70, 2048, 6, 3, 2.10, 4.24, 1.34),
 ("Alexander Isak", "Liverpool", "ST", 0.85, 0.30, 586, 6, 0, 4.70, 0.37, 4.70, 717, 3, 1, 3.25, 0.85, 3.25),
 ("Cody Gakpo", "Liverpool", "W", 0.80, 0.00, 463, 1, 3, 0.88, 1.79, 0.88, 2758, 7, 5, 9.83, 6.59, 9.83),
 ("Bradley Barcola", "Liverpool", "W", 0.70, 0.00, 428, 0, 2, 1.10, 1.00, 1.10, 1778, 11, 1, 11.66, 4.78, 11.66),
 ("Florian Wirtz", "Liverpool", "W", 0.35, 0.10, 630, 0, 2, 1.15, 1.22, 1.15, 2426, 5, 3, 7.58, 5.38, 7.58),
 ("Dominik Szoboszlai", "Liverpool", "CM", 0.50, 0.50, 472, 1, 0, 1.32, 1.42, 0.56, 3236, 6, 7, 4.72, 8.84, 3.96),
 ("Alexis Mac Allister", "Liverpool", "CM", 0.75, 0.00, 581, 0, 0, 0.57, 0.34, 0.57, 2683, 2, 4, 4.07, 2.85, 4.07),
 ("Kylian Mbappé", "Real Madrid", "ST", 0.92, 0.90, 898, 11, 2, 12.33, 1.99, 10.10, 2623, 25, 5, 25.80, 7.24, 19.11),
 ("Vinícius Júnior", "Real Madrid", "W", 0.80, 0.05, 592, 1, 3, 3.59, 2.49, 3.59, 2865, 16, 5, 14.40, 7.16, 10.69),
 ("Arda Güler", "Real Madrid", "W", 0.70, 0.00, 607, 2, 2, 2.24, 4.85, 2.24, 2076, 4, 9, 4.81, 8.85, 4.81),
 ("Jude Bellingham", "Real Madrid", "W", 0.85, 0.00, 790, 3, 3, 1.73, 3.42, 1.73, 1933, 6, 4, 7.73, 3.04, 7.73),
 ("Yan Diomande", "Real Madrid", "W", 0.55, 0.00, 534, 2, 2, 1.21, 0.81, 1.21, 2507, 12, 8, 8.03, 10.05, 8.03),
 ("Erling Haaland", "Man City", "ST", 0.95, 0.90, 711, 9, 0, 7.04, 1.74, 7.04, 2979, 27, 8, 28.80, 5.51, 25.75),
 ("Rayan Cherki", "Man City", "W", 0.75, 0.00, 450, 4, 2, 2.41, 1.98, 2.41, 1792, 4, 12, 4.64, 10.78, 4.64),
 ("Phil Foden", "Man City", "W", 0.70, 0.00, 341, 1, 2, 2.31, 1.94, 2.31, 2083, 7, 5, 6.69, 6.11, 6.69),
 ("Jérémy Doku", "Man City", "W", 0.60, 0.00, 212, 1, 1, 0.50, 2.03, 0.50, 1783, 5, 5, 4.00, 7.55, 4.00),
 ("Iliman Ndiaye", "Man City", "W", 0.50, 0.00, 607, 0, 3, 1.35, 2.41, 1.35, 2805, 6, 3, 6.14, 4.46, 4.62),
 ("Désiré Doué", "Paris SG", "W", 0.85, 0.50, 355, 1, 1, 1.87, 1.06, 1.11, 1372, 7, 4, 8.19, 3.85, 7.43),
 ("Ferran Torres", "Paris SG", "ST", 0.75, 0.10, 429, 4, 1, 2.08, 0.44, 2.08, 2025, 16, 2, 16.18, 3.16, 16.18),
 ("Maghnes Akliouche", "Paris SG", "W", 0.60, 0.00, 400, 1, 0, 1.91, 0.63, 1.91, 2430, 6, 6, 6.61, 5.36, 6.61),
 ("Vitinha", "Paris SG", "CM", 0.90, 0.30, 493, 1, 1, 0.57, 1.46, 0.57, 2122, 1, 7, 0.98, 3.46, 0.98),
 ("Jonathan David", "Atlético", "ST", 0.70, 0.10, 305, 3, 2, 4.05, 1.43, 4.05, 1784, 6, 4, 11.46, 4.23, 10.70),
 ("Álex Baena", "Atlético", "W", 0.85, 0.00, 613, 5, 2, 1.67, 2.98, 1.67, 1615, 2, 3, 1.78, 6.57, 1.78),
 ("Ademola Lookman", "Atlético", "W", 0.65, 0.00, 622, 1, 0, 2.07, 1.06, 2.07, 1441, 6, 0, 8.32, 3.97, 7.57),
 ("Giuliano Simeone", "Atlético", "W", 0.70, 0.00, 686, 2, 2, 1.06, 1.33, 1.06, 2153, 4, 6, 6.10, 5.53, 6.10),
 ("Serhou Guirassy", "Dortmund", "ST", 0.90, 0.85, 615, 2, 2, 4.02, 1.78, 4.02, 2366, 17, 1, 19.91, 1.93, 17.64),
 ("Maximilian Beier", "Dortmund", "W", 0.80, 0.00, 447, 2, 1, 3.28, 0.89, 3.28, 2069, 9, 6, 8.25, 4.96, 8.25),
 ("Ethan Nwaneri", "Dortmund", "W", 0.60, 0.00, 344, 0, 0, 0.86, 1.59, 0.86, 488, 2, 1, 1.22, 1.03, 1.22),
 ("Rasmus Højlund", "Napoli", "ST", 0.85, 0.00, 560, 2, 0, 2.64, 1.87, 2.64, 2784, 13, 5, 13.31, 3.27, 12.55),
 ("Kevin De Bruyne", "Napoli", "W", 0.80, 0.85, 460, 3, 1, 3.05, 2.14, 1.53, 1176, 5, 2, 3.52, 4.02, 1.23),
 ("Scott McTominay", "Napoli", "CM", 0.80, 0.00, 358, 2, 0, 1.32, 0.30, 1.32, 2798, 10, 3, 12.43, 2.01, 11.67),
 ("Matteo Politano", "Napoli", "W", 0.70, 0.00, 445, 1, 2, 1.06, 1.99, 1.06, 2249, 2, 6, 3.13, 5.60, 3.13),
 ("Donyell Malen", "Roma", "ST", 0.90, 0.60, 492, 6, 1, 6.66, 1.08, 6.66, 2099, 18, 3, 19.94, 1.92, 16.90),
 ("Matías Soulé", "Roma", "W", 0.80, 0.30, 502, 3, 1, 2.41, 1.04, 2.41, 2207, 6, 5, 4.68, 4.46, 4.68),
 ("Bruno Fernandes", "Man United", "W", 0.95, 0.90, 630, 3, 1, 3.17, 1.03, 2.41, 3082, 9, 21, 11.93, 17.76, 7.36),
 ("Bryan Mbeumo", "Man United", "W", 0.90, 0.05, 720, 4, 0, 4.26, 1.28, 4.26, 2676, 11, 3, 13.31, 5.09, 13.31),
 ("Matheus Cunha", "Man United", "ST", 0.80, 0.00, 553, 1, 2, 0.85, 1.86, 0.85, 2506, 10, 2, 7.08, 3.70, 7.08),
 ("Christopher Nkunku", "Leipzig", "ST", 0.80, 0.60, 369, 4, 1, 2.97, 0.59, 2.97, 1343, 7, 3, 9.94, 1.61, 6.13),
 ("Antonio Nusa", "Leipzig", "W", 0.85, 0.00, 548, 3, 5, 0.77, 3.64, 0.77, 2048, 4, 3, 5.20, 4.75, 5.20),
 ("Georges Mikautadze", "Villarreal", "ST", 0.70, 0.40, 507, 3, 1, 4.32, 1.29, 3.58, 2335, 14, 6, 16.30, 4.15, 16.30),
 ("Alberto Moleiro", "Villarreal", "W", 0.85, 0.00, 684, 2, 4, 3.56, 3.30, 3.56, 2535, 10, 5, 5.61, 5.78, 5.61),
 ("Ayoze Pérez", "Villarreal", "W", 0.75, 0.30, 676, 1, 3, 4.67, 1.36, 4.67, 1154, 5, 4, 5.86, 2.58, 5.12),
 ("Isco", "Real Betis", "W", 0.70, 0.80, 480, 2, 0, 3.14, 0.88, 2.39, 213, 1, 1, 1.00, 0.62, 0.25),
 ("Abde Ezzalzouli", "Real Betis", "W", 0.75, 0.00, 515, 3, 0, 1.84, 1.26, 1.84, 2275, 10, 8, 10.30, 6.22, 10.30),
 ("Antony", "Real Betis", "W", 0.80, 0.00, 605, 0, 0, 2.83, 0.53, 2.83, 2495, 8, 6, 9.02, 6.64, 9.02),
 ("Tasos Douvikas", "Como", "ST", 0.80, 0.15, 593, 5, 0, 5.54, 0.35, 5.54, 2279, 14, 1, 15.17, 2.24, 14.41),
 ("Nico Paz", "Como", "W", 0.90, 0.70, 586, 2, 2, 2.52, 1.54, 2.52, 2905, 12, 6, 8.90, 7.03, 7.38),
 ("Martin Baturina", "Como", "W", 0.55, 0.00, 342, 2, 1, 0.69, 0.53, 0.69, 1579, 6, 3, 1.90, 6.70, 1.90),
 ("Florian Thauvin", "Lens", "W", 0.90, 0.95, 702, 4, 7, 4.06, 4.20, 1.78, 2510, 11, 6, 12.10, 9.86, 9.82),
 ("Olivier Giroud", "Lille", "ST", 0.60, 0.60, 407, 2, 2, 1.74, 0.19, 0.98, 1610, 7, 1, 8.87, 1.85, 5.83),
 ("Deniz Undav", "Stuttgart", "W", 0.85, 0.40, 436, 0, 0, 1.41, 0.99, 1.41, 2261, 19, 6, 19.06, 5.58, 18.30),
 ("Ermedin Demirović", "Stuttgart", "ST", 0.80, 0.40, 452, 3, 0, 4.29, 0.38, 4.29, 1507, 12, 3, 8.66, 2.18, 7.91),
 ("Chris Führich", "Stuttgart", "W", 0.60, 0.00, 403, 1, 0, 0.48, 2.07, 0.48, 1727, 7, 7, 4.27, 7.83, 4.27),
 ("Bilal El Khannouss", "Stuttgart", "W", 0.55, 0.00, 308, 1, 0, 0.39, 1.66, 0.39, 1654, 4, 5, 3.09, 5.28, 3.09),
 ("Nicolas Jackson", "Aston Villa", "ST", 0.80, 0.00, 561, 4, 0, 2.28, 0.86, 2.28, 991, 8, 1, 8.49, 2.09, 8.49),
 ("John McGinn", "Aston Villa", "W", 0.80, 0.00, 646, 1, 3, 1.10, 0.99, 1.10, 2221, 5, 4, 3.00, 4.86, 3.00),
]

# Defenders (same columns; npxG = xG except for penalty takers). FB = full-back / wing-back, CB = centre-back.
P += [
 ("Gabriel", "Arsenal", "CB", 0.90, 0.00, 720, 1, 0, 2.10, 0.06, 2.10, 2748, 3, 4, 4.65, 2.73, 4.65),
 ("Ezri Konsa", "Arsenal", "CB", 0.75, 0.00, 550, 1, 0, 0.79, 0.04, 0.79, 3036, 0, 0, 1.07, 0.60, 1.07),
 ("Riccardo Calafiori", "Arsenal", "FB", 0.70, 0.00, 619, 1, 2, 1.45, 1.22, 1.45, 1755, 1, 2, 3.47, 0.65, 3.47),
 ("Jurriën Timber", "Arsenal", "FB", 0.60, 0.00, 148, 0, 0, 0.00, 0.11, 0.00, 2475, 3, 5, 4.03, 2.59, 4.03),
 ("Ben White", "Arsenal", "FB", 0.55, 0.00, 543, 0, 3, 0.13, 1.39, 0.13, 703, 0, 1, 0.28, 1.56, 0.28),
 ("Myles Lewis-Skelly", "Arsenal", "FB", 0.40, 0.00, 416, 0, 0, 0.18, 0.19, 0.18, 666, 0, 0, 0.13, 0.18, 0.13),
 ("Pau Cubarsí", "Barcelona", "CB", 0.70, 0.00, 609, 0, 2, 0.24, 0.91, 0.24, 2733, 1, 0, 0.55, 0.44, 0.55),
 ("Gerard Martín", "Barcelona", "CB", 0.80, 0.00, 672, 0, 0, 0.42, 0.35, 0.42, 2145, 0, 0, 0.30, 0.76, 0.30),
 ("João Cancelo", "Barcelona", "FB", 0.70, 0.00, 282, 1, 0, 0.14, 0.51, 0.14, 938, 2, 2, 0.97, 3.25, 0.97),
 ("Xavi Espart", "Barcelona", "FB", 0.65, 0.00, 655, 1, 2, 0.35, 1.54, 0.35, 157, 0, 0, 0.03, 0.00, 0.03),
 ("Ibrahima Konaté", "Real Madrid", "CB", 0.80, 0.00, 810, 0, 0, 0.31, 0.19, 0.31, 3133, 1, 0, 1.96, 0.73, 1.96),
 ("Dean Huijsen", "Real Madrid", "CB", 0.70, 0.00, 684, 0, 0, 0.51, 0.19, 0.51, 2046, 2, 2, 2.33, 1.15, 2.33),
 ("Antonio Rüdiger", "Real Madrid", "CB", 0.40, 0.00, 304, 1, 0, 0.15, 0.14, 0.15, 1501, 1, 0, 1.41, 0.31, 1.41),
 ("Marc Cucurella", "Real Madrid", "FB", 0.75, 0.00, 650, 0, 0, 0.00, 0.22, 0.00, 2714, 1, 4, 1.89, 4.54, 1.89),
 ("Trent Alexander-Arnold", "Real Madrid", "FB", 0.45, 0.00, 259, 0, 1, 0.18, 0.87, 0.18, 1175, 0, 4, 0.40, 2.03, 0.40),
 ("Denzel Dumfries", "Real Madrid", "FB", 0.50, 0.00, 454, 0, 0, 0.63, 0.23, 0.63, 1332, 3, 1, 3.65, 1.41, 3.65),
 ("Julian Ryerson", "Dortmund", "FB", 0.85, 0.00, 509, 0, 0, 0.05, 2.52, 0.05, 2288, 0, 15, 1.09, 10.86, 1.09),
 ("Nico Schlotterbeck", "Dortmund", "CB", 0.85, 0.00, 440, 1, 0, 0.81, 0.25, 0.81, 2520, 5, 1, 3.80, 1.06, 3.80),
 ("Waldemar Anton", "Dortmund", "CB", 0.85, 0.00, 630, 0, 1, 0.07, 0.36, 0.07, 2880, 2, 0, 1.85, 0.45, 1.85),
 ("Daniel Svensson", "Dortmund", "FB", 0.50, 0.00, 608, 1, 0, 0.70, 0.30, 0.70, 2454, 2, 2, 2.93, 4.30, 2.93),
 ("Joško Gvardiol", "Man City", "FB", 0.85, 0.00, 576, 1, 3, 1.41, 1.64, 1.41, 1374, 2, 2, 1.86, 0.44, 1.86),
 ("Nico O'Reilly", "Man City", "FB", 0.50, 0.00, 292, 0, 0, 1.12, 0.09, 1.12, 2646, 5, 3, 6.73, 3.85, 6.73),
 ("Marc Guéhi", "Man City", "CB", 0.85, 0.00, 677, 1, 1, 0.71, 0.62, 0.71, 3150, 3, 3, 4.70, 2.73, 4.70),
 ("Rúben Dias", "Man City", "CB", 0.80, 0.00, 720, 0, 0, 0.28, 0.38, 0.28, 2142, 2, 0, 0.44, 0.42, 0.44),
 ("Matheus Nunes", "Man City", "FB", 0.50, 0.00, 379, 0, 0, 0.00, 0.00, 0.00, 2865, 1, 5, 0.68, 3.10, 0.68),
 ("Virgil van Dijk", "Liverpool", "CB", 0.90, 0.00, 720, 0, 0, 0.17, 0.06, 0.17, 3420, 6, 0, 4.89, 0.33, 4.89),
 ("Jérémy Jacquet", "Liverpool", "CB", 0.70, 0.00, 690, 0, 0, 0.15, 0.06, 0.15, 1678, 0, 0, 0.79, 0.57, 0.79),
 ("Milos Kerkez", "Liverpool", "FB", 0.80, 0.00, 657, 0, 0, 0.08, 0.08, 0.08, 2271, 2, 1, 1.39, 1.86, 1.39),
 ("Ronald Araújo", "Liverpool", "CB", 0.60, 0.00, 504, 0, 0, 0.06, 0.05, 0.06, 1049, 3, 0, 2.30, 0.60, 2.30),
 ("Federico Dimarco", "Inter", "WB", 0.80, 0.00, 481, 0, 1, 1.18, 2.48, 1.18, 2709, 7, 16, 7.29, 15.93, 7.29),
 ("Carlos Augusto", "Inter", "FB", 0.65, 0.00, 346, 2, 2, 1.10, 1.49, 1.10, 1745, 1, 1, 1.96, 1.14, 1.96),
 ("Andy Diouf", "Inter", "FB", 0.60, 0.00, 530, 0, 4, 0.24, 2.00, 0.24, 552, 1, 0, 1.12, 1.75, 1.12),
 ("Manuel Akanji", "Inter", "CB", 0.85, 0.00, 596, 0, 1, 1.24, 1.35, 1.24, 2814, 2, 0, 2.30, 0.33, 2.30),
 ("Yann Bisseck", "Inter", "CB", 0.80, 0.00, 547, 1, 0, 0.55, 0.28, 0.55, 1924, 3, 1, 2.83, 0.65, 2.83),
 ("Achraf Hakimi", "Paris SG", "FB", 0.85, 0.00, 410, 0, 0, 1.11, 0.62, 1.11, 1382, 2, 2, 2.80, 1.46, 2.80),
 ("Willian Pacho", "Paris SG", "CB", 0.85, 0.00, 450, 0, 0, 0.04, 0.00, 0.04, 1910, 0, 0, 0.41, 0.09, 0.41),
 ("Illia Zabarnyi", "Paris SG", "CB", 0.70, 0.00, 180, 1, 0, 0.41, 0.02, 0.41, 2387, 1, 0, 0.57, 0.16, 0.57),
 ("Álex Grimaldo", "Atlético", "WB", 0.85, 0.80, 760, 3, 2, 2.57, 1.79, 1.08, 2539, 8, 7, 6.76, 10.24, 4.49),
 ("David Raum", "Leipzig", "FB", 0.90, 0.00, 540, 0, 0, 0.14, 1.84, 0.14, 2570, 3, 7, 2.40, 11.04, 1.64),
 ("Maximilian Mittelstädt", "Stuttgart", "FB", 0.80, 0.30, 528, 1, 1, 0.46, 2.27, 0.46, 2200, 6, 4, 4.95, 5.52, 1.92),
 ("Héctor Bellerín", "Real Betis", "FB", 0.80, 0.00, 673, 0, 1, 0.85, 0.89, 0.85, 1822, 2, 3, 0.54, 3.85, 0.54),
 ("Dayot Upamecano", "Bayern", "CB", 0.85, 0.00, 588, 2, 0, 1.91, 0.38, 1.91, 1805, 1, 1, 0.83, 1.44, 0.83),
 ("Jonathan Tah", "Bayern", "CB", 0.75, 0.00, 365, 0, 0, 0.65, 0.02, 0.65, 2031, 2, 1, 0.66, 0.59, 0.66),
 ("Alphonso Davies", "Bayern", "FB", 0.70, 0.00, 373, 0, 2, 0.15, 2.03, 0.15, 521, 1, 3, 0.44, 1.30, 0.44),
]

# Opponent expected goals in this match (analyst estimate from odds) -> clean sheet = exp(-x).
XGA = {"Arsenal": 0.75, "Real Madrid": 0.90, "Barcelona": 0.95, "Dortmund": 1.00, "Man City": 1.01, "Liverpool": 1.03, "Inter": 1.09, "Paris SG": 1.14, "Bayern": 1.23, "Man United": 1.31, "Como": 1.35, "Napoli": 1.39, "Roma": 1.55, "Stuttgart": 1.60, "Lens": 1.60, "Atlético": 1.65, "Lille": 1.66, "Real Betis": 1.69, "Villarreal": 2.03, "Leipzig": 2.06, "Aston Villa": 2.97}
# Predicted goalkeepers: (name, team, P(start))
GKS = [("David Raya", "Arsenal", .97), ("Joan García", "Barcelona", .95), ("Thibaut Courtois", "Real Madrid", .85),
       ("Gregor Kobel", "Dortmund", .95), ("Gianluigi Donnarumma", "Man City", .95), ("Alisson", "Liverpool", .95),
       ("Josep Martínez", "Inter", .90), ("Matvey Safonov", "Paris SG", .85), ("Jonas Urbig", "Bayern", .85)]
# Central / attacking midfielders. Everyone else with pos ST or W is a forward (strikers and wingers).
MIDS = {"Ismael Saibari", "Lennart Karl", "Fermín López", "Pedri", "Martin Ødegaard", "Declan Rice", "Hakan Çalhanoğlu",
        "Nicolò Barella", "Piotr Zieliński", "Florian Wirtz", "Dominik Szoboszlai", "Alexis Mac Allister", "Arda Güler",
        "Jude Bellingham", "Rayan Cherki", "Phil Foden", "Vitinha", "Álex Baena", "Ethan Nwaneri", "Kevin De Bruyne",
        "Scott McTominay", "Bruno Fernandes", "Isco", "Nico Paz", "Martin Baturina", "Deniz Undav", "Bilal El Khannouss",
        "John McGinn"}
DEF_AS_FB = {"Federico Dimarco", "Álex Grimaldo"}


def prob(lam):
    return 1 - math.exp(-lam)


rows = []
RATES, FORM = {}, {}   # per-90 rates and this season's league form, for the page's radar and scatter
LAMS = {}              # expected goals and assists in this match, P(start): inputs for Fantasy points
for (name, team, pos, ps, pen, m1, g1, a1, xg1, xa1, np1, m0, g0, a0, xg0, xa0, np0) in P:
    opp, ha, mxg, txg1, tg1, txg0, tg0 = TEAMS[team]
    base = (txg1 + PREV_W * txg0) / (tg1 + PREV_W * tg0)   # team league xG per game
    mult = mxg / base                                       # opponent / venue adjustment
    if name in PREV_TEAM_XG:
        sc = min(1.33, max(0.75, base / PREV_TEAM_XG[name]))
        g0, a0, xg0, xa0, np0 = (v * sc for v in (g0, a0, xg0, xa0, np0))
    eff = m1 + PREV_W * m0
    w = eff / (eff + K_MIN)
    pr_g, pr_a = PRIOR[pos]
    r_np = (np1 + PREV_W * np0 + pr_g * K_MIN / 90) / ((eff + K_MIN) / 90)
    r_xa = (xa1 + PREV_W * xa0 + pr_a * K_MIN / 90) / ((eff + K_MIN) / 90)
    RATES[name] = (r_np, r_xa)
    FORM[name] = (g1 + a1) / m1 * 90 if m1 >= 250 else None   # goals + assists per 90, league, this season
    f_g = (g1 + PREV_W * g0 + FINISH_C) / (xg1 + PREV_W * xg0 + FINISH_C)
    f_a = (a1 + PREV_W * a0 + FINISH_C) / (xa1 + PREV_W * xa0 + FINISH_C)
    mins = ps * MIN_IF_START[pos] + (1 - ps) * SUB_MIN
    share = mins / 90
    lam_g = r_np * f_g * mult * share + PEN_PER_XG * mxg * PEN_CONV * pen * share
    lam_a = r_xa * f_a * mult * share
    lam = lam_g + lam_a
    LAMS[name] = (lam_g, lam_a, ps)
    band = WIDE_BAND if name in WIDE else BAND
    rows.append((prob(lam), name, team, opp, ha, pos, ps, mins, prob(lam_g), prob(lam_a),
                 prob(lam * (1 - band)), prob(lam * (1 + band)), w, lam, r_np + r_xa, mult))

rows.sort(reverse=True)
print(f"{'#':>2} {'Player':22} {'Team':12} {'Opp':18} HA Pos  Pst  Min  P(G)  P(A)  P(G/A)  range     w    lam  rate90 mult")
for i, r in enumerate(rows, 1):
    p, name, team, opp, ha, pos, ps, mins, pg, pa, lo, hi, w, lam, rate, mult = r
    print(f"{i:>2} {name:22} {team:12} {opp:18} {ha}  {pos:3} {ps:.2f} {mins:4.0f}  {pg:4.0%}  {pa:4.0%}  {p:5.1%}  "
          f"[{lo:.0%}-{hi:.0%}]  {w:.2f} {lam:.2f}  {rate:.2f}  {mult:.2f}")


# ---------------------------------------------------------------- XI by position (4-3-3)
# "Shine": GK = clean sheet; DEF = clean sheet or a goal/assist; MID / FWD = goal or assist.
cands = []
for r in rows:
    p, name, team, opp, ha, pos, ps, mins, pg, pa, lo, hi, w, lam, rate, mult = r
    if pos in ("FB", "CB") or name in DEF_AS_FB:
        role = "CB" if pos == "CB" else "FB"
        cs = math.exp(-XGA[team]) * ps
        shine = 1 - (1 - cs) * (1 - p)
        slo = 1 - (1 - math.exp(-XGA[team] * (1 + BAND)) * ps) * (1 - lo)
        shi = 1 - (1 - math.exp(-XGA[team] * (1 - BAND)) * ps) * (1 - hi)
        cands.append(dict(name=name, team=team, opp=opp, ha=ha, line="DEF", role=role, shine=shine, cs=cs,
                          pG=pg, pA=pa, pGA=p, lo=slo, hi=shi, mins=mins, ps=ps))
    else:
        line = "MID" if name in MIDS else "FWD"
        cands.append(dict(name=name, team=team, opp=opp, ha=ha, line=line, role=pos, shine=p, cs=None,
                          pG=pg, pA=pa, pGA=p, lo=lo, hi=hi, mins=mins, ps=ps))
for name, team, ps in GKS:
    opp, ha = TEAMS[team][0], TEAMS[team][1]
    cs = math.exp(-XGA[team]) * ps
    cands.append(dict(name=name, team=team, opp=opp, ha=ha, line="GK", role="GK", shine=cs, cs=cs, pG=0, pA=0,
                      pGA=0, lo=math.exp(-XGA[team] * 1.2) * ps, hi=math.exp(-XGA[team] * 0.8) * ps,
                      mins=ps * 90, ps=ps))
cands.sort(key=lambda c: -c["shine"])


def pick(pool, used):
    """GK 1, FB 2, CB 2, MID 3, FWD 3; at most 2 defenders from one club."""
    xi, need, club_def = [], {"GK": 1, "FB": 2, "CB": 2, "MID": 3, "FWD": 3}, {}
    for c in pool:
        slot = c["role"] if c["line"] == "DEF" else c["line"]
        if c["name"] in used or need.get(slot, 0) == 0:
            continue
        if c["line"] == "DEF" and club_def.get(c["team"], 0) >= 2:
            continue
        xi.append(c)
        need[slot] -= 1
        used.add(c["name"])
        if c["line"] == "DEF":
            club_def[c["team"]] = club_def.get(c["team"], 0) + 1
    return xi


def pct(v):
    return None if v is None else round(v * 100)


used = set()
xi1 = pick(cands, used)
xi2 = pick(cands, used)
for label, xi in (("FIRST XI", xi1), ("SECOND XI", xi2)):
    print("\n" + label + f"  (expected to shine: {sum(c['shine'] for c in xi):.1f})")
    for c in sorted(xi, key=lambda c: ["GK", "DEF", "MID", "FWD"].index(c["line"])):
        print(f"  {c['line']:3} {c['role']:3} {c['name']:24} {c['team']:12} {c['ha']} {c['opp']:18} shine {pct(c['shine']):3}% "
              f"[{pct(c['lo'])}-{pct(c['hi'])}]  CS {pct(c['cs'])}  G/A {pct(c['pGA'])} (G {pct(c['pG'])} A {pct(c['pA'])})  min {c['mins']:.0f}")
print("\nNEXT UP BY LINE")
for line in ("GK", "DEF", "MID", "FWD"):
    rest = [c for c in cands if c["line"] == line and c["name"] not in used][:5]
    print(" ", line, "; ".join(f"{c['name']} ({c['team']}, {c['role']}) {pct(c['shine'])}% [{pct(c['lo'])}-{pct(c['hi'])}] CS {pct(c['cs'])} GA {pct(c['pGA'])}" for c in rest))


# ---------------------------------------------------------------- numbers the web page needs
# Written to ucl_md4_page_data.json: per-90 rates, form and opponent xG for the 22 picked players (radar),
# and every modelled outfield player for the scatter plot.
import json

page = {"players": {}, "pool": []}
for c in cands:
    if c["line"] == "GK":
        continue
    xg90, xa90 = RATES[c["name"]]
    tag = 1 if c in xi1 else 2 if c in xi2 else 0
    form = FORM[c["name"]]
    page["pool"].append([c["name"], c["team"], c["line"], round(xg90, 2), round(xa90, 2), pct(c["shine"]), tag,
                         None if form is None else round(form, 2), round(c["mins"]), XGA[c["team"]]])
for c in xi1 + xi2:
    r = RATES.get(c["name"])
    form = FORM.get(c["name"])
    page["players"][c["name"]] = {
        "xg90": None if r is None else round(r[0], 2), "xa90": None if r is None else round(r[1], 2),
        "form": None if form is None else round(form, 2), "oppXg": XGA[c["team"]], "teamXg": TEAMS[c["team"]][2]}

# ---------------------------------------------------------------- best Fantasy lineup
# UEFA Champions League Fantasy. Only players whose Fantasy position and price could be verified from
# published sources (1 Sep - 13 Oct 2026; not re-checked for Matchday 4) are eligible: name -> (position, price in EUR m).
FANTASY = {
    "David Raya": ("GK", 6.0), "Alisson": ("GK", 6.0), "Thibaut Courtois": ("GK", 6.0), "Josep Martínez": ("GK", 4.5),
    "Gabriel": ("DEF", 6.0), "Virgil van Dijk": ("DEF", 6.0), "Riccardo Calafiori": ("DEF", 4.5),
    "Federico Dimarco": ("DEF", 5.0), "Alphonso Davies": ("DEF", 5.0), "Dayot Upamecano": ("DEF", 5.5),
    "Álex Grimaldo": ("DEF", 6.0), "Marc Cucurella": ("DEF", 6.0), "Jonathan Tah": ("DEF", 5.0),
    "Joško Gvardiol": ("DEF", 5.5), "Dean Huijsen": ("DEF", 4.5), "Maximilian Mittelstädt": ("DEF", 4.5),
    "Achraf Hakimi": ("DEF", 6.0),
    "Lamine Yamal": ("MID", 10.0), "Michael Olise": ("MID", 9.0), "Florian Wirtz": ("MID", 8.5), "Rayan Cherki": ("MID", 7.0),
    "Nico Paz": ("MID", 7.0), "Ismael Saibari": ("MID", 6.5), "Kevin De Bruyne": ("MID", 7.0),
    "Bruno Fernandes": ("MID", 9.0), "Vinícius Júnior": ("MID", 9.5), "Florian Thauvin": ("MID", 6.5),
    "Harry Kane": ("FWD", 11.0), "Erling Haaland": ("FWD", 11.0), "Kylian Mbappé": ("FWD", 11.0),
    "Deniz Undav": ("FWD", 7.0), "Serhou Guirassy": ("FWD", 8.5),
}
GOAL_PTS = {"GK": 6, "DEF": 6, "MID": 5, "FWD": 4}
CS_PTS = {"GK": 4, "DEF": 4, "MID": 1, "FWD": 0}
XI_BUDGET = 83.0          # of the 100m squad budget, leaving 17m for the four bench players (assumption)
FORMATIONS = [(3, 4, 3), (3, 5, 2), (4, 3, 3), (4, 4, 2), (4, 5, 1), (5, 3, 2), (5, 4, 1)]
CLUB_MAX = 3


def conceded_penalty(mu):
    """Expected value of floor(goals conceded / 2) for Poisson(mu): -1 point per two conceded."""
    return sum((k // 2) * math.exp(-mu) * mu ** k / math.factorial(k) for k in range(12))


GK_START = {n: p for n, _, p in GKS}
GK_TEAM = {n: t for n, t, _ in GKS}
TEAM_OF = {r[1]: r[2] for r in rows}
TEAM_OF.update(GK_TEAM)
fan = []
for name, (fpos, price) in FANTASY.items():
    team = TEAM_OF[name]
    lam_g, lam_a, ps = LAMS.get(name, (0.0, 0.0, GK_START.get(name, 0.0)))
    p_play, p60 = ps + (1 - ps) * 0.7, ps * 0.85
    xp = p_play + p60 + GOAL_PTS[fpos] * lam_g + 3 * lam_a + CS_PTS[fpos] * math.exp(-XGA[team]) * p60
    if fpos in ("GK", "DEF"):
        xp -= conceded_penalty(XGA[team]) * ps
    fan.append(dict(name=name, team=team, opp=TEAMS[team][0], ha=TEAMS[team][1], fpos=fpos, price=price, xp=xp))


def best_xi(pool):
    """Exact search: knapsack over price for each formation, then branch if a club has more than CLUB_MAX."""
    best = None
    for d, m, f in FORMATIONS:
        need = {"GK": 1, "DEF": d, "MID": m, "FWD": f}
        states = {(0, 0, 0, 0, 0): (0.0, ())}           # (cost in half-millions, gk, def, mid, fwd) -> (points, picks)
        for i, p in enumerate(pool):
            cost, idx = int(round(p["price"] * 2)), "GK DEF MID FWD".split().index(p["fpos"])
            for key, (pts, picks) in list(states.items()):
                cnt = list(key[1:])
                if cnt[idx] >= need[p["fpos"]] or key[0] + cost > XI_BUDGET * 2:
                    continue
                cnt[idx] += 1
                nk = (key[0] + cost, *cnt)
                if nk not in states or states[nk][0] < pts + p["xp"]:
                    states[nk] = (pts + p["xp"], picks + (i,))
        for key, (pts, picks) in states.items():
            if key[1:] == (1, d, m, f) and (best is None or pts > best[0]):
                best = (pts, picks, (d, m, f))
    if best is None:
        return None
    pts, picks, form = best
    clubs = {}
    for i in picks:
        clubs.setdefault(pool[i]["team"], []).append(i)
    over = [v for v in clubs.values() if len(v) > CLUB_MAX]
    if not over:
        return pts, [pool[i] for i in picks], form
    options = [best_xi([q for j, q in enumerate(pool) if j != i]) for i in over[0]]
    options = [o for o in options if o]
    return max(options, key=lambda o: o[0]) if options else None


fan.sort(key=lambda p: -p["xp"])
fx_pts, fx_team, fx_form = best_xi(fan)
captain = max(fx_team, key=lambda p: p["xp"])
print("\nBEST FANTASY XI  %d-%d-%d  from %d priced players" % (*fx_form, len(fan)))
for p in sorted(fx_team, key=lambda p: ("GK DEF MID FWD".split().index(p["fpos"]), -p["xp"])):
    print(f"  {p['fpos']:3} {p['name']:22} {p['team']:12} {p['ha']} {p['opp']:18} EUR {p['price']:4.1f}m  xPts {p['xp']:.2f}"
          + ("  (captain)" if p is captain else ""))
fx_cost = sum(p["price"] for p in fx_team)
print(f"  cost {fx_cost:.1f}m of {XI_BUDGET:.0f}m, expected points {fx_pts:.1f}, with captain doubled {fx_pts + captain['xp']:.1f}")
print("  all priced players:", "; ".join(f"{p['name']} {p['xp']:.1f}" for p in fan))
# The best Fantasy lineup is subscribers-only from Matchday 3 on: it goes to the git-ignored briefs/ folder,
# never into the public page data.
fantasy = {"formation": "%d-%d-%d" % fx_form, "points": round(fx_pts, 1), "withCaptain": round(fx_pts + captain["xp"], 1),
           "cost": fx_cost, "budget": XI_BUDGET, "eligible": len(fan), "captain": captain["name"],
           "players": [dict(p, xp=round(p["xp"], 1)) for p in fx_team],
           "all": [dict(p, xp=round(p["xp"], 1)) for p in fan]}
import os
os.makedirs("briefs", exist_ok=True)
with open(os.path.join("briefs", "ucl_md4_fantasy.json"), "w", encoding="utf-8") as fh:
    json.dump(fantasy, fh, ensure_ascii=False, indent=1)

with open("ucl_md4_page_data.json", "w", encoding="utf-8") as fh:
    json.dump(page, fh, ensure_ascii=False, indent=1)
print("\nwrote ucl_md4_page_data.json:", len(page["pool"]), "outfield players in the pool; Fantasy lineup in briefs/")
