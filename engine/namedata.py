"""Name/nationality/hometown pools for procedurally generated fighters.

All names are generic/fictional combinations — not drawn from any real
fighter's name or nickname — used purely to populate the starter universe.
"""

NATIONALITIES = {
    "United States": {
        "m_first": ["Marcus", "Tyler", "Jordan", "Cody", "Derek", "Brandon", "Austin", "Trevor", "Shane", "Dustin"],
        "f_first": ["Megan", "Brianna", "Kayla", "Sydney", "Ashley", "Courtney", "Paige", "Morgan", "Taylor", "Jenna"],
        "last": ["Carter", "Whitfield", "Nolan", "Hargrove", "Beckett", "Sawyer", "Donovan", "Kessler", "Pruitt", "Landry", "Griggs", "Maddox"],
        "cities": ["Denver, Colorado", "Albuquerque, New Mexico", "Sacramento, California", "Tulsa, Oklahoma", "Erie, Pennsylvania"],
    },
    "Brazil": {
        "m_first": ["Rafael", "Thiago", "Bruno", "Eduardo", "Vinicius", "Leandro", "Diego", "Fabricio", "Gustavo", "Adriano"],
        "f_first": ["Camila", "Fernanda", "Larissa", "Juliana", "Beatriz", "Patricia", "Aline", "Vanessa", "Renata", "Simone"],
        "last": ["Almeida", "Barros", "Cavalcante", "Teixeira", "Moraes", "Nascimento", "Pereira", "Duarte", "Fontes", "Ribeiro", "Andrade", "Correia"],
        "cities": ["Recife, Brazil", "Curitiba, Brazil", "Belo Horizonte, Brazil", "Manaus, Brazil", "Porto Alegre, Brazil"],
    },
    "Russia": {
        "m_first": ["Ivan", "Dmitri", "Sergei", "Maxim", "Artem", "Nikolai", "Yuri", "Vitaly", "Roman", "Pavel"],
        "f_first": ["Yelena", "Irina", "Natalia", "Oksana", "Svetlana", "Anastasia", "Marina", "Olga", "Ksenia", "Daria"],
        "last": ["Volkov", "Sokolov", "Petrov", "Morozov", "Belyaev", "Kuznetsov", "Orlov", "Zaitsev", "Popov", "Yakovlev", "Egorov", "Bogdanov"],
        "cities": ["Grozny, Russia", "Krasnodar, Russia", "Khabarovsk, Russia", "Ufa, Russia", "Yekaterinburg, Russia"],
    },
    "Japan": {
        "m_first": ["Kenji", "Hiroshi", "Takumi", "Shota", "Daisuke", "Ryota", "Yuto", "Kazuki", "Sora", "Haruto"],
        "f_first": ["Aya", "Mika", "Yuki", "Sakura", "Nanami", "Hina", "Rin", "Airi", "Kaori", "Yui"],
        "last": ["Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Saito", "Matsumoto", "Inoue", "Kimura", "Hayashi", "Sato"],
        "cities": ["Osaka, Japan", "Sapporo, Japan", "Fukuoka, Japan", "Nagoya, Japan", "Yokohama, Japan"],
    },
    "Ireland": {
        "m_first": ["Sean", "Cian", "Declan", "Rory", "Fionn", "Eoin", "Darragh", "Cathal", "Aidan", "Niall"],
        "f_first": ["Aoife", "Niamh", "Saoirse", "Ciara", "Roisin", "Orla", "Sinead", "Grainne", "Maeve", "Fiona"],
        "last": ["Byrne", "Doyle", "Kavanagh", "Walsh", "Molloy", "Cusack", "Fahey", "Brennan", "Hanley", "Costello", "Reidy", "Dunphy"],
        "cities": ["Cork, Ireland", "Galway, Ireland", "Limerick, Ireland", "Waterford, Ireland", "Kilkenny, Ireland"],
    },
    "England": {
        "m_first": ["Callum", "Jack", "Oliver", "Harvey", "George", "Lewis", "Charlie", "Ben", "Ryan", "Connor"],
        "f_first": ["Molly", "Chloe", "Amelia", "Freya", "Grace", "Ellie", "Poppy", "Millie", "Katie", "Hannah"],
        "last": ["Higgins", "Marsh", "Whitfield", "Pemberton", "Sutcliffe", "Rowntree", "Ashworth", "Prescott", "Hargreaves", "Winstanley", "Fairclough", "Bramwell"],
        "cities": ["Manchester, England", "Leeds, England", "Sheffield, England", "Birmingham, England", "Bristol, England"],
    },
    "Poland": {
        "m_first": ["Marek", "Tomasz", "Krzysztof", "Pawel", "Wojciech", "Grzegorz", "Bartosz", "Kamil", "Rafal", "Adrian"],
        "f_first": ["Agnieszka", "Katarzyna", "Malgorzata", "Ewa", "Joanna", "Magdalena", "Anna", "Beata", "Justyna", "Monika"],
        "last": ["Kowalski", "Wisniewski", "Wojcik", "Kaminski", "Lewandowski", "Zielinski", "Szymanski", "Wozniak", "Dabrowski", "Kozlowski", "Mazur", "Krawczyk"],
        "cities": ["Krakow, Poland", "Wroclaw, Poland", "Gdansk, Poland", "Poznan, Poland", "Lodz, Poland"],
    },
    "Nigeria": {
        "m_first": ["Chidi", "Emeka", "Tunde", "Obinna", "Kelechi", "Ifeanyi", "Uche", "Segun", "Bayo", "Chuka"],
        "f_first": ["Amara", "Ngozi", "Folake", "Chinwe", "Adaeze", "Yemisi", "Zainab", "Ada", "Bisi", "Oluchi"],
        "last": ["Okafor", "Adeyemi", "Balogun", "Eze", "Okonkwo", "Nwosu", "Afolabi", "Ibekwe", "Uzoma", "Adeleke", "Okoro", "Nnamdi"],
        "cities": ["Lagos, Nigeria", "Ibadan, Nigeria", "Enugu, Nigeria", "Kano, Nigeria", "Benin City, Nigeria"],
    },
    "Mexico": {
        "m_first": ["Alejandro", "Emilio", "Rodrigo", "Santiago", "Mateo", "Gael", "Ivan", "Ricardo", "Fernando", "Cesar"],
        "f_first": ["Ximena", "Valentina", "Fernanda", "Camila", "Daniela", "Regina", "Paola", "Andrea", "Alejandra", "Sofia"],
        "last": ["Reyes", "Cortez", "Salazar", "Aguilar", "Zamora", "Villareal", "Cabrera", "Munoz", "Delgado", "Guerrero", "Contreras", "Vega"],
        "cities": ["Guadalajara, Mexico", "Monterrey, Mexico", "Tijuana, Mexico", "Puebla, Mexico", "Merida, Mexico"],
    },
    "South Korea": {
        "m_first": ["Min-jun", "Ji-ho", "Seung-woo", "Dong-hyun", "Jae-won", "Hyun-woo", "Tae-yang", "Sung-min", "Joon-ho", "Kyung-soo"],
        "f_first": ["Ji-woo", "Seo-yeon", "Min-ji", "Ha-eun", "Yoo-jin", "Eun-ji", "Su-bin", "Ye-jin", "Da-eun", "Chae-won"],
        "last": ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Yoon", "Han", "Song", "Shin", "Oh", "Bae"],
        "cities": ["Busan, South Korea", "Incheon, South Korea", "Daegu, South Korea", "Gwangju, South Korea", "Daejeon, South Korea"],
    },
    "Kazakhstan": {
        "m_first": ["Nurlan", "Yerlan", "Askar", "Daulet", "Bekzat", "Almas", "Serik", "Timur", "Marat", "Talgat"],
        "f_first": ["Aigerim", "Dana", "Zhanel", "Saltanat", "Alma", "Gulnara", "Aizhan", "Diana", "Ainur", "Bota"],
        "last": ["Nurgaliyev", "Abenov", "Zhaksybekov", "Serikov", "Tulegenov", "Kairatuly", "Bekov", "Dzhaksybekov", "Amanzholov", "Sagatov", "Yesenov", "Orazbayev"],
        "cities": ["Almaty, Kazakhstan", "Shymkent, Kazakhstan", "Astana, Kazakhstan", "Karaganda, Kazakhstan", "Aktobe, Kazakhstan"],
    },
    "Canada": {
        "m_first": ["Liam", "Ethan", "Mason", "Owen", "Logan", "Carter", "Wyatt", "Hunter", "Dawson", "Cole"],
        "f_first": ["Emma", "Ava", "Charlotte", "Olivia", "Mackenzie", "Brooklyn", "Alexis", "Kayley", "Sadie", "Jocelyn"],
        "last": ["Tremblay", "Gagnon", "Doiron", "Boucher", "Lachance", "Fontaine", "Lemieux", "Turcotte", "Bergeron", "Pelletier", "Girard", "Cormier"],
        "cities": ["Toronto, Canada", "Calgary, Canada", "Winnipeg, Canada", "Halifax, Canada", "Edmonton, Canada"],
    },
    "Australia": {
        "m_first": ["Jayden", "Riley", "Lachlan", "Kai", "Bailey", "Flynn", "Hayden", "Beau", "Jarrah", "Cooper"],
        "f_first": ["Isla", "Matilda", "Ruby", "Willow", "Piper", "Harper", "Ivy", "Zali", "Indie", "Skye"],
        "last": ["McAllister", "Ferris", "Whitlam", "Bracewell", "Kingsley", "Rutherford", "Calloway", "Fenwick", "Ashcroft", "Merrick", "Delaney", "Trewin"],
        "cities": ["Brisbane, Australia", "Perth, Australia", "Adelaide, Australia", "Newcastle, Australia", "Gold Coast, Australia"],
    },
    "Sweden": {
        "m_first": ["Erik", "Anders", "Gustav", "Filip", "Viktor", "Oskar", "Emil", "Linus", "Axel", "Hampus"],
        "f_first": ["Elin", "Sara", "Ingrid", "Klara", "Freja", "Alva", "Stina", "Wilma", "Signe", "Maja"],
        "last": ["Lindqvist", "Bergstrom", "Nilsson", "Karlsson", "Sandberg", "Holm", "Fransson", "Osterberg", "Wallin", "Lundgren", "Ekstrom", "Soderberg"],
        "cities": ["Gothenburg, Sweden", "Malmo, Sweden", "Uppsala, Sweden", "Vasteras, Sweden", "Orebro, Sweden"],
    },
    "Georgia": {
        "m_first": ["Giorgi", "Levan", "Nika", "Davit", "Beka", "Zurab", "Irakli", "Sandro", "Otar", "Luka"],
        "f_first": ["Nino", "Tamar", "Mariam", "Ana", "Salome", "Keti", "Nana", "Elene", "Tea", "Sofio"],
        "last": ["Beridze", "Kapanadze", "Lomidze", "Tsiklauri", "Gogoladze", "Chkheidze", "Mamaladze", "Kiknadze", "Sordia", "Abashidze", "Dolidze", "Machavariani"],
        "cities": ["Tbilisi, Georgia", "Batumi, Georgia", "Kutaisi, Georgia", "Rustavi, Georgia", "Gori, Georgia"],
    },
}

NICKNAMES = [
    "The Hammer", "Iron", "The Storm", "Relentless", "The Machine", "Blackout",
    "The Wolf", "Grit", "The Wall", "Nightmare", "The Ghost", "Fury",
    "The Butcher", "Timber", "The Viper", "Chaos", "The Anchor", "Reckoning",
    "The Cyclone", "Payback", "The Executioner", "Ruthless", "The Bull", "Havoc",
    "The Surgeon", "Warhead", "The Prophet", "Landslide", "The Panther", "Deadbolt",
    "The Warden", "Sledgehammer", "The Menace", "Ironclad", "The Reaper", "Diesel",
    "The Sniper", "Bedlam", "The Juggernaut", "Vendetta",
]
