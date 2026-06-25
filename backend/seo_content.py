"""Contenuti SEO seed per la prova server-side.
Le pagine vengono generate dai dati (qui mostrati come seed iniziale);
in produzione gli stessi documenti arrivano dal CMS / sync YouTube,
SENZA modificare il codice."""

SEED_EPISODES = [
    {
        "slug": "fabio-ceravolo-130-gol-carriera",
        "type": "intervista",
        "type_label": "Intervista",
        "section": "interviste",
        "section_label": "Interviste",
        "title": "Fabio Ceravolo si racconta a UnoXdue",
        "h1": "Fabio Ceravolo: 130 gol, Reggina, Atalanta e la magia del Benevento",
        "seo_title": "Intervista Fabio Ceravolo | UnoXdue Podcast Serie A",
        "meta_description": "Fabio Ceravolo ospite di UnoXdue: 130 gol in carriera, le radici calabresi, Reggina, Atalanta e la storica promozione in Serie A con il Benevento.",
        "youtube_id": "7035L7empWg",
        "duration": "1:12:40",
        "published_at": "2026-06-24",
        "published_human": "24 giugno 2026",
        "thumbnail": "https://img.youtube.com/vi/7035L7empWg/maxresdefault.jpg",
        "guest_name": "Fabio Ceravolo",
        "excerpt": "Dalla Reggina all'Atalanta fino alla storica promozione in Serie A con il Benevento: l'ex attaccante di Locri si racconta a UnoXdue tra radici, sacrificio e ricordi indimenticabili.",
        "summary": [
            "Ospite del podcast UnoXdue, condotto da Antonello Santopaolo insieme ai tipster il Ninja e il Marziano, Fabio Ceravolo ha ripercorso i passaggi più significativi della sua carriera.",
            "Spazio al legame profondo con la Calabria e con Locri, una terra dura che forma il carattere, e alla stagione magica vissuta a Benevento culminata con la promozione in Serie A.",
            "Nel racconto trovano posto anche i compagni di quella cavalcata, da Ciciretti a Viola, e il valore di un gruppo capace di scrivere una pagina di storia del calcio italiano.",
        ],
        "topics": ["Serie A", "Benevento", "Reggina", "Atalanta", "Calabria", "Promozione"],
        "chapters": [
            {"time": "00:00", "label": "Introduzione e benvenuto"},
            {"time": "04:30", "label": "Le radici in Calabria e Locri"},
            {"time": "21:10", "label": "Reggina e Atalanta"},
            {"time": "38:45", "label": "La magia del Benevento e la Serie A"},
            {"time": "58:20", "label": "Ciciretti, Viola e il gruppo"},
        ],
        "quotes": [
            "La Calabria è una terra meravigliosa ma difficile: lì nessuno ti regala niente.",
            "Al Benevento vivemmo una stagione magica, quasi irreale.",
        ],
        "participants": [
            {"slug": "antonello-santopaolo", "name": "Antonello Santopaolo", "role": "Host"},
            {"slug": "il-ninja", "name": "Il Ninja", "role": "Tipster"},
            {"slug": "il-marziano", "name": "Il Marziano", "role": "Tipster"},
        ],
        "prediction_url": None,
        "related": [
            {"section": "interviste", "slug": "allan-baclet-playoff-cosenza", "title": "Allan Baclet: i playoff e il sogno Serie B col Cosenza"},
        ],
    },
    {
        "slug": "allan-baclet-playoff-cosenza",
        "type": "intervista",
        "type_label": "Intervista",
        "section": "interviste",
        "section_label": "Interviste",
        "title": "Allan Baclet ricorda i playoff col Cosenza",
        "h1": "Allan Baclet: i playoff e il sogno Serie B col Cosenza",
        "seo_title": "Intervista Allan Baclet | UnoXdue Podcast",
        "meta_description": "Allan Baclet ospite di UnoXdue: la cavalcata playoff del 2018 che riportò il Cosenza in Serie B dopo 15 anni. «Avremmo vinto anche contro la Juventus».",
        "youtube_id": "MxHqU7AK97I",
        "duration": "58:12",
        "published_at": "2026-06-05",
        "published_human": "5 giugno 2026",
        "thumbnail": "https://img.youtube.com/vi/MxHqU7AK97I/maxresdefault.jpg",
        "guest_name": "Allan Baclet",
        "excerpt": "L'ex centravanti francese ripercorre la cavalcata che riportò i lupi tra i cadetti dopo 15 anni di attesa, tra ricordi, gol decisivi e consapevolezza crescente.",
        "summary": [
            "Ospite di UnoXdue, Allan Baclet ha riaperto l'album dei ricordi della stagione 2017-2018, quando con cinque gol nei playoff trascinò il Cosenza verso la Serie B.",
            "Dalla sfida con la Sicula Leonzio alla finale di Pescara contro il Siena, il racconto di un gruppo che partita dopo partita capì di poter scrivere la storia.",
        ],
        "topics": ["Cosenza", "Playoff", "Serie B", "Serie C", "Pescara"],
        "chapters": [
            {"time": "00:00", "label": "Introduzione"},
            {"time": "06:15", "label": "L'avvio dei playoff"},
            {"time": "25:40", "label": "La finale di Pescara"},
            {"time": "41:00", "label": "Il gruppo e la città"},
        ],
        "quotes": [
            "Quell'anno potevamo giocare con la Juventus e avremmo vinto: avevamo qualcosa in più.",
        ],
        "participants": [
            {"slug": "antonello-santopaolo", "name": "Antonello Santopaolo", "role": "Host"},
            {"slug": "il-ninja", "name": "Il Ninja", "role": "Tipster"},
            {"slug": "il-marziano", "name": "Il Marziano", "role": "Tipster"},
        ],
        "prediction_url": None,
        "related": [
            {"section": "interviste", "slug": "fabio-ceravolo-130-gol-carriera", "title": "Fabio Ceravolo: 130 gol, Reggina, Atalanta e la magia del Benevento"},
        ],
    },
]


SEED_TEAM = [
    {
        "slug": "sono-micuccio", "name": "Sono Micuccio", "badge": "Il pioniere",
        "role": "Fondatore & analista", "photo": "/hosts/host2.jpg", "is_host": False,
        "order": 1,
        "bio": "Fondatore del progetto Aperiquattro. Pioniere nell'analisi dei campionati minori, si distingue per le sue analisi avanzate sui palinsesti sportivi, sempre fuori dagli schemi e ad alto potenziale.",
        "instagram": "https://www.instagram.com/sonomicuccioreal/",
    },
    {
        "slug": "il-ninja", "name": "Il Ninja", "badge": "Lo specialista",
        "role": "Specialista basket", "photo": "/hosts/host3.jpg", "is_host": False,
        "order": 2,
        "bio": "Specialista del basket: quando c'e' un tiro libero decisivo, e' sempre pronto a colpire. Segue le gare fino all'alba senza mai perdere un colpo. Precisione, dedizione e un fiuto infallibile.",
        "instagram": "https://www.instagram.com/ilniinja/",
    },
    {
        "slug": "il-marziano", "name": "Il Marziano", "badge": "Il veterano",
        "role": "Tipster veterano", "photo": "/hosts/host1.jpg", "is_host": False,
        "order": 3,
        "bio": "Figura storica nel panorama dei tipster italiani. Le sue giocate si distinguono per precisione e competenza, sempre accompagnate dal suo marchio di fabbrica: gli iconici Shooters.",
        "instagram": "https://www.instagram.com/il.marziano_/",
    },
    {
        "slug": "antonello-santopaolo", "name": "Antonello Santopaolo", "badge": "La voce di UnoXdue",
        "role": "Host", "photo": "/team/antonello.jpg", "is_host": True, "order": 4,
        "bio": "Web content writer e moderatore di eventi, Antonello Santopaolo conduce e coordina le conversazioni di UnoXdue. Da anni opera nella comunicazione digitale, realizzando interviste e approfondimenti con professionisti e personalita' del panorama italiano. E' la voce che tiene insieme il podcast, anche quando preferisce restare fuori dall'inquadratura.",
        "instagram": None,
    },
]

SEED_PREDICTIONS = [
    {
        "competition": "Serie A", "season": "2025-2026", "round": 38,
        "intro": "Le giocate del nostro team per l'ultima giornata di Serie A. Quote indicative al momento della pubblicazione: possono variare.",
        "updated_at": "21/05/2026 12:20", "status": "pubblicato", "episode_url": None,
        "picks": [
            {"tipster": "Il Marziano", "type": "Multipla", "total_odds": "17.63", "selections": [
                {"competition": "Serie A", "date": "22/05 20:45", "match": "Fiorentina - Atalanta", "market": "Multigol 2-4", "pick": "Si", "odds": "1.49"},
                {"competition": "Serie A", "date": "23/05 20:45", "match": "Lazio - Pisa", "market": "Multigol 1-2 1T", "pick": "Si", "odds": "1.55"},
                {"competition": "Serie A", "date": "24/05 18:00", "match": "Napoli - Udinese", "market": "1X2 + U/O 3,5", "pick": "1 + Under", "odds": "2.09"},
                {"competition": "Serie A", "date": "24/05 20:45", "match": "Lecce - Genoa", "market": "Multigol Casa 1-3", "pick": "Si", "odds": "1.35"},
                {"competition": "Serie A", "date": "24/05 20:45", "match": "Cremonese - Como", "market": "Goal/No Goal", "pick": "Goal", "odds": "1.78"},
                {"competition": "Serie A", "date": "24/05 20:45", "match": "Verona - Roma", "market": "1X2 + U/O 1,5", "pick": "2 + Over", "odds": "1.52"},
            ]},
            {"tipster": "Sono Micuccio", "type": "Multipla", "total_odds": "6.42", "selections": [
                {"competition": "Serie A", "date": "24/05 20:45", "match": "Inter - Torino", "market": "1X2", "pick": "1", "odds": "1.40"},
                {"competition": "Serie A", "date": "23/05 18:00", "match": "Bologna - Sassuolo", "market": "Over 2,5", "pick": "Over", "odds": "1.72"},
                {"competition": "Serie A", "date": "24/05 20:45", "match": "Juventus - Milan", "market": "Goal/No Goal", "pick": "Goal", "odds": "1.70"},
            ]},
            {"tipster": "Il Ninja", "type": "Multipla", "total_odds": "4.18", "selections": [
                {"competition": "Serie A", "date": "24/05 20:45", "match": "Atalanta - Parma", "market": "1X2", "pick": "1", "odds": "1.45"},
                {"competition": "Serie A", "date": "23/05 20:45", "match": "Roma - Empoli", "market": "Multigol Casa 1-3", "pick": "Si", "odds": "1.36"},
                {"competition": "Serie A", "date": "24/05 18:00", "match": "Como - Cagliari", "market": "Under 3,5", "pick": "Under", "odds": "2.12"},
            ]},
        ],
    },
]
