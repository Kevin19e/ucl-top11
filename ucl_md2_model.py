"""UCL 2026/27 Matchday 2 (13-14 Oct 2026): P(goal or assist) per player.

Inputs were collected by hand on 2026-10-12 from:
  - Understat league pages (2026/27 to date and 2025/26 full season): minutes, goals,
    assists, xG, xA, npxG. Domestic league only (top-5 leagues).
  - UEFA.com predicted line-ups / absences article (12 Oct 2026) for start probabilities.
  - Bookmaker 1X2 / totals prices (12 Oct 2026) for the team match-xG assumptions.
START, PEN_SHARE and MATCH_XG are analyst judgements, not measured data.
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
WIDE = {"Deniz Undav", "Ousmane Dembele", "Ismael Saibari", "Kai Havertz", "Florian Wirtz",
        "Nicolas Jackson", "Isco"}

# Players who changed club: last season's numbers were produced in a different attack.
# Value = previous club's league xG per game; last-season stats are rescaled by
# clip(current team baseline / previous, 0.75, 1.33).
PREV_TEAM_XG = {
    "Nicolas Jackson": 3.08, "Antoine Semenyo": 1.90, "Christopher Nkunku": 1.71,
    "Jonathan David": 1.95, "Anthony Gordon": 1.59, "Karim Adeyemi": 1.99,
    "Ferran Torres": 2.62, "Alex Grimaldo": 2.21, "Donyell Malen": 1.60,
    "Ezri Konsa": 1.48, "Marc Cucurella": 1.90, "Kostas Tsimikas": 1.65, "Yan Couto": 1.99,
}

# position prior per 90: (npxG, xA)
PRIOR = {"ST": (0.40, 0.12), "W": (0.25, 0.20), "CM": (0.10, 0.12), "WB": (0.06, 0.12),
         "FB": (0.04, 0.10), "CB": (0.05, 0.02)}
MIN_IF_START = {"ST": 76, "W": 74, "CM": 80, "WB": 84, "FB": 84, "CB": 88}

# team: (opponent, H/A, match xG assumption, xG 26/27, games 26/27, xG 25/26, games 25/26)
TEAMS = {
    "Bayern":      ("Viking", "A", 3.00, 17.90, 5, 104.8, 34),
    "Barcelona":   ("Galatasaray", "A", 2.60, 32.32, 8, 99.7, 38),
    "Arsenal":     ("Lille", "H", 2.20, 11.73, 6, 77.5, 38),
    "Inter":       ("Club Brugge", "H", 2.50, 18.47, 6, 87.1, 38),
    "Liverpool":   ("LASK", "A", 2.10, 9.00, 6, 67.3, 38),
    "Real Madrid": ("Roma", "A", 1.80, 21.09, 8, 81.5, 38),
    "Roma":        ("Real Madrid", "H", 1.15, 17.24, 6, 62.6, 38),
    "Man City":    ("Paris SG", "H", 1.75, 12.63, 6, 79.4, 38),
    "Paris SG":    ("Man City", "A", 1.55, 15.17, 6, 75.6, 34),
    "Stuttgart":   ("Slovan Bratislava", "A", 2.30, 10.70, 5, 68.3, 34),
    "Dortmund":    ("Bodo/Glimt", "A", 1.60, 11.21, 5, 67.8, 34),
    "Atletico":    ("Man United", "H", 1.60, 15.70, 8, 68.1, 38),
    "Man United":  ("Atletico", "A", 1.10, 11.45, 6, 72.2, 38),
    "Leipzig":     ("PSV", "H", 2.10, 13.48, 5, 75.2, 34),
    "Villarreal":  ("Napoli", "H", 1.50, 20.14, 8, 68.8, 38),
    "Napoli":      ("Villarreal", "A", 1.20, 12.42, 6, 57.8, 38),
    "Como":        ("Feyenoord", "A", 1.70, 13.40, 6, 68.0, 38),
    "Aston Villa": ("Fenerbahce", "H", 1.60, 6.83, 6, 56.2, 38),
    "Lens":        ("Sporting CP", "H", 1.40, 13.91, 6, 74.4, 34),
    "Real Betis":  ("Porto", "H", 1.50, 15.81, 8, 61.3, 38),
}

# name, team, pos, P(start), pen share,
#   26/27: min, G, A, xG, xA, npxG | 25/26: min, G, A, xG, xA, npxG
P = [
 ("Harry Kane", "Bayern", "ST", .85, .95, 386, 3, 3, 4.25, 2.12, 3.49, 2385, 36, 5, 29.6, 7.4, 21.2),
 ("Michael Olise", "Bayern", "W", .85, .05, 391, 4, 1, 2.39, 1.80, 2.39, 2308, 15, 19, 11.5, 17.0, 11.5),
 ("Luis Diaz", "Bayern", "W", .80, 0, 355, 1, 0, 2.73, 1.46, 2.73, 2464, 15, 14, 14.9, 10.1, 14.9),
 ("Ismael Saibari", "Bayern", "W", .70, 0, 253, 2, 2, 2.17, 1.60, 2.17, 0, 0, 0, 0, 0, 0),
 ("Lamine Yamal", "Barcelona", "W", .90, .85, 682, 7, 5, 6.39, 5.06, 4.91, 2291, 16, 11, 14.7, 12.6, 11.7),
 ("Anthony Gordon", "Barcelona", "W", .75, 0, 492, 1, 4, 2.88, 1.78, 2.88, 1888, 6, 2, 8.8, 3.7, 6.5),
 ("Dani Olmo", "Barcelona", "W", .70, .10, 302, 0, 3, 1.28, 3.22, 1.28, 2109, 7, 8, 8.8, 6.7, 8.8),
 ("Fermin Lopez", "Barcelona", "W", .35, 0, 479, 4, 2, 2.91, 2.12, 2.91, 1780, 6, 9, 7.5, 7.6, 7.5),
 ("Karim Adeyemi", "Barcelona", "W", .30, 0, 237, 2, 2, 4.29, 1.54, 4.29, 1218, 7, 4, 5.2, 3.5, 5.2),
 ("Bukayo Saka", "Arsenal", "W", .85, .80, 512, 3, 0, 4.59, 0.40, 3.83, 2239, 7, 5, 8.7, 8.6, 7.9),
 ("Martin Odegaard", "Arsenal", "W", .80, .15, 481, 2, 0, 1.79, 1.97, 1.79, 1347, 1, 6, 1.2, 5.0, 1.2),
 ("Kai Havertz", "Arsenal", "ST", .60, 0, 508, 2, 0, 1.58, 0.39, 1.58, 582, 2, 3, 4.9, 1.5, 4.9),
 ("Lautaro Martinez", "Inter", "ST", .85, .10, 352, 4, 0, 5.35, 0.99, 5.35, 2205, 17, 6, 17.1, 6.3, 17.1),
 ("Marcus Thuram", "Inter", "ST", .80, 0, 287, 3, 2, 3.69, 1.03, 3.69, 1933, 13, 6, 11.9, 4.5, 11.9),
 ("Federico Dimarco", "Inter", "WB", .80, 0, 397, 0, 1, 1.04, 2.02, 1.04, 2709, 7, 16, 7.3, 15.9, 7.3),
 ("Hakan Calhanoglu", "Inter", "CM", .80, .85, 199, 3, 0, 0.87, 0.69, 0.11, 1674, 9, 4, 5.1, 3.5, 1.3),
 ("Florian Wirtz", "Liverpool", "W", .90, .30, 472, 0, 1, 1.07, 0.62, 1.07, 2426, 5, 3, 7.6, 5.4, 7.6),
 ("Kylian Mbappe", "Real Madrid", "ST", .90, .90, 720, 7, 2, 9.23, 1.81, 7.74, 2623, 25, 5, 25.8, 7.2, 19.1),
 ("Vinicius Junior", "Real Madrid", "W", .85, .05, 592, 1, 3, 3.59, 2.49, 3.59, 2865, 16, 5, 14.4, 7.2, 10.7),
 ("Arda Guler", "Real Madrid", "W", .70, 0, 436, 1, 2, 2.01, 3.96, 2.01, 2076, 4, 9, 4.8, 8.8, 4.8),
 ("Jude Bellingham", "Real Madrid", "W", .85, 0, 627, 3, 2, 1.65, 2.81, 1.65, 1933, 6, 4, 7.7, 3.0, 7.7),
 ("Donyell Malen", "Roma", "ST", .90, .60, 407, 6, 0, 6.41, 0.89, 6.41, 2099, 18, 3, 19.9, 1.9, 16.9),
 ("Paulo Dybala", "Roma", "W", .80, .35, 503, 0, 4, 2.30, 4.29, 2.30, 1360, 2, 6, 6.3, 6.4, 5.5),
 ("Erling Haaland", "Man City", "ST", .95, .90, 531, 6, 0, 5.11, 0.63, 5.11, 2979, 27, 8, 28.8, 5.5, 25.8),
 ("Rayan Cherki", "Man City", "W", .80, 0, 403, 4, 2, 2.01, 1.89, 2.01, 1792, 4, 12, 4.6, 10.8, 4.6),
 ("Phil Foden", "Man City", "W", .70, 0, 219, 0, 2, 1.56, 1.29, 1.56, 2083, 7, 5, 6.7, 6.1, 6.7),
 ("Antoine Semenyo", "Man City", "W", .80, 0, 540, 2, 3, 0.42, 1.69, 0.42, 3220, 17, 4, 12.8, 4.1, 11.3),
 ("Ousmane Dembele", "Paris SG", "ST", .80, .40, 172, 0, 1, 1.72, 0.55, 1.72, 1050, 10, 7, 6.6, 5.2, 4.3),
 ("Khvicha Kvaratskhelia", "Paris SG", "W", .80, 0, 273, 1, 1, 1.64, 1.32, 1.64, 1477, 8, 4, 8.0, 5.7, 7.2),
 ("Desire Doue", "Paris SG", "W", .70, .20, 230, 0, 1, 1.32, 1.00, 0.56, 1372, 7, 4, 8.2, 3.9, 7.4),
 ("Ferran Torres", "Paris SG", "ST", .30, 0, 297, 2, 0, 1.45, 0.19, 1.45, 2025, 16, 2, 16.2, 3.2, 16.2),
 ("Ermedin Demirovic", "Stuttgart", "ST", .85, .40, 284, 1, 0, 2.53, 0.38, 2.53, 1507, 12, 3, 8.7, 2.2, 7.9),
 ("Deniz Undav", "Stuttgart", "W", .85, .40, 316, 0, 0, 0.41, 0.99, 0.41, 2261, 19, 6, 19.1, 5.6, 18.3),
 ("Chris Fuhrich", "Stuttgart", "W", .70, 0, 291, 1, 0, 0.42, 1.17, 0.42, 1727, 7, 7, 4.3, 7.8, 4.3),
 ("Serhou Guirassy", "Dortmund", "ST", .90, .85, 435, 2, 2, 2.57, 1.70, 2.57, 2366, 17, 1, 19.9, 1.9, 17.6),
 ("Maximilian Beier", "Dortmund", "W", .80, 0, 359, 1, 1, 2.87, 0.80, 2.87, 2069, 9, 6, 8.2, 5.0, 8.2),
 ("Jonathan David", "Atletico", "ST", .75, .10, 215, 3, 2, 3.26, 1.34, 3.26, 1784, 6, 4, 11.5, 4.2, 10.7),
 ("Alex Baena", "Atletico", "W", .80, 0, 495, 4, 2, 1.49, 2.09, 1.49, 1615, 2, 3, 1.8, 6.6, 1.8),
 ("Alex Grimaldo", "Atletico", "WB", .80, .80, 626, 3, 1, 2.53, 1.00, 1.05, 2539, 8, 7, 6.8, 10.2, 4.5),
 ("Bruno Fernandes", "Man United", "W", .95, .90, 540, 3, 1, 3.08, 0.98, 2.32, 3082, 9, 21, 11.9, 17.8, 7.4),
 ("Bryan Mbeumo", "Man United", "W", .90, .05, 540, 3, 0, 3.29, 1.27, 3.29, 2676, 11, 3, 13.3, 5.1, 13.3),
 ("Matheus Cunha", "Man United", "ST", .85, 0, 507, 1, 2, 0.67, 1.85, 0.67, 2506, 10, 2, 7.1, 3.7, 7.1),
 ("Christopher Nkunku", "Leipzig", "ST", .80, .60, 321, 4, 1, 2.97, 0.59, 2.97, 1343, 7, 3, 9.9, 1.6, 6.1),
 ("Antonio Nusa", "Leipzig", "W", .85, 0, 413, 3, 3, 0.68, 3.11, 0.68, 2048, 4, 3, 5.2, 4.7, 5.2),
 ("Georges Mikautadze", "Villarreal", "ST", .75, .40, 465, 2, 1, 4.05, 1.27, 3.31, 2155, 13, 6, 15.1, 4.1, 15.1),
 ("Alberto Moleiro", "Villarreal", "W", .80, 0, 574, 2, 3, 2.30, 2.81, 2.30, 2535, 10, 5, 5.6, 5.8, 5.6),
 ("Gerard Moreno", "Villarreal", "ST", .70, .50, 391, 2, 0, 2.75, 1.75, 2.00, 1368, 10, 0, 7.0, 3.0, 4.8),
 ("Rasmus Hojlund", "Napoli", "ST", .85, 0, 437, 2, 0, 1.70, 1.05, 1.70, 2784, 13, 5, 13.3, 3.3, 12.6),
 ("Kevin De Bruyne", "Napoli", "W", .75, .85, 347, 3, 1, 2.21, 1.47, 1.45, 1176, 5, 2, 3.5, 4.0, 1.2),
 ("Tasos Douvikas", "Como", "ST", .80, .15, 413, 2, 0, 3.78, 0.35, 3.78, 2279, 14, 1, 15.2, 2.2, 14.4),
 ("Nico Paz", "Como", "W", .90, .70, 517, 1, 1, 2.28, 1.41, 2.28, 2905, 12, 6, 8.9, 7.0, 7.4),
 ("Nicolas Jackson", "Aston Villa", "ST", .80, 0, 388, 2, 0, 1.36, 0.67, 1.36, 991, 8, 1, 8.5, 2.1, 8.5),
 ("Florian Thauvin", "Lens", "W", .90, .95, 540, 3, 4, 3.97, 2.25, 1.69, 2510, 11, 6, 12.1, 9.9, 9.8),
 ("Isco", "Real Betis", "W", .80, .80, 412, 2, 0, 3.14, 0.74, 2.39, 0, 0, 0, 0, 0, 0),
 ("Abde Ezzalzouli", "Real Betis", "W", .80, 0, 335, 2, 0, 1.39, 1.10, 1.39, 2275, 10, 8, 10.3, 6.2, 10.3),
]

# Defenders (same columns; npxG = xG except for penalty takers). FB = full-back / wing-back, CB = centre-back.
P += [
 ("Jurrien Timber", "Arsenal", "FB", .80, 0, 128, 0, 0, 0.00, 0.00, 0.00, 2475, 3, 5, 4.0, 2.6, 4.0),
 ("Ezri Konsa", "Arsenal", "CB", .80, 0, 370, 0, 0, 0.08, 0.04, 0.08, 3036, 0, 0, 1.1, 0.6, 1.1),
 ("Gabriel", "Arsenal", "CB", .90, 0, 540, 0, 0, 1.03, 0.03, 1.03, 2748, 3, 4, 4.6, 2.7, 4.6),
 ("Riccardo Calafiori", "Arsenal", "FB", .80, 0, 509, 1, 2, 1.45, 1.22, 1.45, 1755, 1, 2, 3.5, 0.6, 3.5),
 ("Konrad Laimer", "Bayern", "FB", .80, 0, 180, 0, 0, 0.42, 0.08, 0.42, 1997, 3, 9, 2.8, 5.0, 2.8),
 ("Dayot Upamecano", "Bayern", "CB", .85, 0, 408, 1, 0, 1.00, 0.14, 1.00, 1805, 1, 1, 0.8, 1.4, 0.8),
 ("Jonathan Tah", "Bayern", "CB", .80, 0, 275, 0, 0, 0.65, 0.00, 0.65, 2031, 2, 1, 0.7, 0.6, 0.7),
 ("Alphonso Davies", "Bayern", "FB", .80, 0, 360, 0, 2, 0.15, 1.91, 0.15, 521, 1, 3, 0.4, 1.3, 0.4),
 ("Jeremie Frimpong", "Liverpool", "FB", .75, 0, 195, 0, 0, 0.01, 0.56, 0.01, 1027, 0, 1, 0.5, 2.7, 0.5),
 ("Virgil van Dijk", "Liverpool", "CB", .90, 0, 540, 0, 0, 0.12, 0.01, 0.12, 3420, 6, 0, 4.9, 0.3, 4.9),
 ("Joe Gomez", "Liverpool", "CB", .70, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
 ("Kostas Tsimikas", "Liverpool", "FB", .70, 0, 63, 0, 0, 0.04, 0.00, 0.04, 617, 0, 0, 0.6, 0.1, 0.6),
 ("Yann Bisseck", "Inter", "CB", .80, 0, 367, 1, 0, 0.55, 0.11, 0.55, 1924, 3, 1, 2.8, 0.7, 2.8),
 ("Manuel Akanji", "Inter", "CB", .85, 0, 416, 0, 1, 1.14, 0.75, 1.14, 2814, 2, 0, 2.3, 0.3, 2.3),
 ("Alessandro Bastoni", "Inter", "CB", .85, 0, 400, 0, 0, 0.21, 0.66, 0.21, 2269, 1, 4, 1.7, 3.2, 1.7),
 ("Andy Diouf", "Inter", "FB", .80, 0, 421, 0, 3, 0.16, 1.85, 0.16, 462, 1, 0, 0.9, 1.8, 0.9),
 ("Jules Kounde", "Barcelona", "FB", .85, 0, 253, 1, 0, 0.82, 0.05, 0.82, 2247, 1, 3, 2.2, 4.6, 2.2),
 ("Pau Cubarsi", "Barcelona", "CB", .90, 0, 429, 0, 0, 0.24, 0.00, 0.24, 2733, 1, 0, 0.6, 0.4, 0.6),
 ("Gerard Martin", "Barcelona", "CB", .80, 0, 529, 0, 0, 0.09, 0.35, 0.09, 2145, 0, 0, 0.3, 0.8, 0.3),
 ("Joao Cancelo", "Barcelona", "FB", .80, 0, 192, 1, 0, 0.14, 0.11, 0.14, 938, 2, 2, 1.0, 3.3, 1.0),
 ("Josha Vagnoman", "Stuttgart", "FB", .85, 0, 446, 2, 1, 0.81, 0.60, 0.81, 1589, 1, 3, 3.6, 2.1, 3.6),
 ("Finn Jeltsch", "Stuttgart", "CB", .85, 0, 377, 0, 1, 0.84, 0.50, 0.84, 1501, 0, 1, 0.2, 0.1, 0.2),
 ("Julian Chabot", "Stuttgart", "CB", .60, 0, 418, 1, 0, 1.03, 0.00, 1.03, 2307, 0, 0, 1.6, 0.3, 1.6),
 ("Maximilian Mittelstadt", "Stuttgart", "FB", .55, .30, 438, 1, 1, 0.46, 2.23, 0.46, 2200, 6, 4, 5.0, 5.5, 1.9),
 ("David Hancko", "Atletico", "CB", .85, 0, 566, 0, 2, 0.50, 0.36, 0.50, 2443, 0, 2, 1.6, 2.2, 1.6),
 ("Marcos Llorente", "Atletico", "FB", .85, 0, 551, 0, 1, 0.23, 0.42, 0.23, 2190, 0, 4, 2.2, 4.2, 2.2),
 ("Trent Alexander-Arnold", "Real Madrid", "FB", .80, 0, 258, 0, 1, 0.18, 0.87, 0.18, 1175, 0, 4, 0.4, 2.0, 0.4),
 ("Dean Huijsen", "Real Madrid", "CB", .85, 0, 504, 0, 0, 0.51, 0.19, 0.51, 2046, 2, 2, 2.3, 1.1, 2.3),
 ("Marc Cucurella", "Real Madrid", "FB", .80, 0, 470, 0, 0, 0.00, 0.17, 0.00, 2714, 1, 4, 1.9, 4.5, 1.9),
 ("Matty Cash", "Aston Villa", "FB", .85, 0, 381, 0, 0, 0.08, 0.04, 0.08, 3040, 3, 3, 1.2, 3.2, 1.2),
 ("Pau Torres", "Aston Villa", "CB", .80, 0, 193, 0, 0, 0.00, 0.00, 0.00, 1679, 0, 0, 1.6, 0.0, 1.6),
 ("Hector Bellerin", "Real Betis", "FB", .85, 0, 596, 0, 1, 0.49, 0.89, 0.49, 1822, 2, 3, 0.5, 3.9, 0.5),
 ("Marc Bartra", "Real Betis", "CB", .85, 0, 333, 1, 0, 0.21, 0.02, 0.21, 1973, 1, 0, 0.8, 0.1, 0.8),
 ("David Raum", "Leipzig", "FB", .90, 0, 450, 0, 0, 0.11, 1.63, 0.11, 2570, 3, 7, 2.4, 11.0, 1.6),
 ("Josko Gvardiol", "Man City", "FB", .85, 0, 459, 1, 3, 0.51, 1.57, 0.51, 1374, 2, 2, 1.9, 0.4, 1.9),
 ("Nuno Mendes", "Paris SG", "FB", .85, 0, 180, 0, 0, 0.19, 2.20, 0.19, 1251, 4, 5, 3.8, 5.1, 3.1),
 ("Yan Couto", "Como", "FB", .85, 0, 512, 0, 1, 0.35, 1.12, 0.35, 989, 2, 2, 1.0, 2.8, 1.0),
]

# Opponent expected goals in this match (analyst estimate from odds) -> clean sheet = exp(-x).
XGA = {"Arsenal": 0.53, "Bayern": 0.75, "Liverpool": 0.75, "Inter": 0.90, "Barcelona": 0.95,
       "Stuttgart": 1.00, "Aston Villa": 1.00, "Atletico": 1.10, "Real Madrid": 1.15, "Real Betis": 1.15,
       "Como": 1.20, "Villarreal": 1.20, "Dortmund": 1.30, "Leipzig": 1.40, "Lens": 1.40, "Napoli": 1.50,
       "Man City": 1.55, "Man United": 1.60, "Paris SG": 1.75, "Roma": 1.80}
# Predicted goalkeepers: (name, team, P(start))
GKS = [("David Raya", "Arsenal", .97), ("Jonas Urbig", "Bayern", .70), ("Alisson", "Liverpool", .95),
       ("Josep Martinez", "Inter", .90), ("Joan Garcia", "Barcelona", .95), ("Dennis Seimen", "Stuttgart", .60),
       ("Zion Suzuki", "Aston Villa", .90), ("Jan Oblak", "Atletico", .95), ("Thibaut Courtois", "Real Madrid", .95),
       ("Alvaro Valles", "Real Betis", .95)]
# Central / attacking midfielders. Everyone else with pos ST or W is a forward (strikers and wingers).
MIDS = {"Ismael Saibari", "Dani Olmo", "Fermin Lopez", "Martin Odegaard", "Hakan Calhanoglu", "Florian Wirtz",
        "Arda Guler", "Jude Bellingham", "Rayan Cherki", "Phil Foden", "Deniz Undav", "Alex Baena",
        "Bruno Fernandes", "Kevin De Bruyne", "Nico Paz", "Isco"}
DEF_AS_FB = {"Federico Dimarco", "Alex Grimaldo"}


def prob(lam):
    return 1 - math.exp(-lam)


rows = []
RATES, FORM = {}, {}   # per-90 rates and this season's league form, for the page's radar and scatter
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
# Written to ucl_md2_page_data.json: per-90 rates, form and opponent xG for the 22 picked players (radar),
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
                         None if form is None else round(form, 2)])
for c in xi1 + xi2:
    r = RATES.get(c["name"])
    form = FORM.get(c["name"])
    page["players"][c["name"]] = {
        "xg90": None if r is None else round(r[0], 2), "xa90": None if r is None else round(r[1], 2),
        "form": None if form is None else round(form, 2), "oppXg": XGA[c["team"]], "teamXg": TEAMS[c["team"]][2]}
with open("ucl_md2_page_data.json", "w", encoding="utf-8") as fh:
    json.dump(page, fh, ensure_ascii=False, indent=1)
print("\nwrote ucl_md2_page_data.json:", len(page["pool"]), "outfield players in the pool")
