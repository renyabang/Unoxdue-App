// Mock data per UnoXdue — facilmente modificabile.
// NOTA: tutti i contenuti qui sono statici (mock). In una fase successiva
// si potranno gestire da un pannello admin/CMS con backend.

export const brand = {
  name: "UnoXdue",
  logo: "/logo.jpg",
  tagline: "Podcast di Calcio & Serie A",
  title: "Il Podcast del Calcio Italiano",
  description:
    "Analisi, pronostici e dibattito sulla Serie A. Tre voci, un'unica passione per il calcio.",
};

export const navLinks = [
  { label: "Home", href: "#home" },
  { label: "Il podcast", href: "#about" },
  { label: "Episodi", href: "#episodi" },
  { label: "Interviste", href: "#interviste" },
  { label: "Pronostici", href: "#pronostici" },
  { label: "Il team", href: "#team" },
  { label: "Parlano di noi", href: "#press" },
];

export const socials = [
  {
    key: "twitch",
    label: "Twitch",
    handle: "@unoxdue_",
    desc: "Dirette live ogni settimana",
    url: "https://www.twitch.tv/unoxdue_",
    color: "#9146FF",
  },
  {
    key: "youtube",
    label: "YouTube",
    handle: "@unoXdue",
    desc: "Episodi completi e interviste",
    url: "https://www.youtube.com/@unoXdue",
    color: "#FF0000",
  },
  {
    key: "instagram",
    label: "Instagram",
    handle: "@unoxdue_",
    desc: "Clip, news e dietro le quinte",
    url: "https://www.instagram.com/unoxdue_",
    color: "#E1306C",
  },
  {
    key: "tiktok",
    label: "TikTok",
    handle: "@unoxdue_",
    desc: "I momenti migliori in breve",
    url: "https://www.tiktok.com/@unoxdue_",
    color: "#111111",
  },
];

export const aboutText = [
  "UnoXdue è il podcast sulla Serie A con tre tipster e un host: analisi tattica, pronostici e dibattito appassionato si incontrano per offrirti uno sguardo unico sul mondo del calcio italiano.",
  "Ogni settimana Sono Micuccio, il Ninja e il Marziano si ritrovano in diretta insieme all'host Antonello Santopaolo per discutere della Serie A, analizzare le partite più importanti e confrontarsi sui temi caldi del calcio italiano ed europeo.",
  "Dalle giornate di campionato ai palinsesti, dalle giocate alle interviste ai protagonisti, UnoXdue è il punto di ritrovo per tutti gli appassionati che cercano contenuti autentici e approfonditi.",
];

export const features = [
  {
    icon: "radio",
    title: "Dirette settimanali",
    text: "Live su Twitch con analisi e dibattito in tempo reale.",
  },
  {
    icon: "target",
    title: "Focus Serie A",
    text: "Approfondimenti su tutte le partite del campionato italiano.",
  },
  {
    icon: "users",
    title: "Tre tipster e un host",
    text: "Quattro punti di vista diversi per un'analisi completa.",
  },
  {
    icon: "clapperboard",
    title: "Contenuti multipli",
    text: "Clip, highlights e contenuti esclusivi su tutti i social.",
  },
];

// UnoXdue Intervista — interviste esclusive ai calciatori (YouTube)
export const interviews = [
  {
    id: "ceravolo",
    player: "Fabio Ceravolo",
    role: "Attaccante — 130 gol in carriera",
    title: "Ceravolo si racconta: 130 gol, Reggina, Atalanta e la magia del Benevento",
    excerpt:
      "Dalla Reggina all'Atalanta fino alla storica promozione in Serie A con il Benevento. Tra radici calabresi, sacrificio e ricordi indimenticabili.",
    youtubeId: "7035L7empWg",
    duration: "Episodio completo",
    tags: ["Serie A", "Benevento", "Reggina"],
  },
  {
    id: "baclet",
    player: "Allan Baclet",
    role: "Ex attaccante Cosenza",
    title: "Baclet senza filtri: Cosenza, i playoff e il sogno Serie B",
    excerpt:
      "L'ex centravanti francese ripercorre la cavalcata che riportò i lupi tra i cadetti dopo 15 anni: «Avremmo vinto anche contro la Juventus».",
    youtubeId: "MxHqU7AK97I",
    duration: "Episodio completo",
    tags: ["Cosenza", "Playoff", "Serie B"],
  },
];

// Ultimi contenuti dai vari canali
export const episodes = [
  {
    id: "ep1",
    platform: "YouTube",
    type: "youtube",
    youtubeId: "b0xDcw9mYNM",
    duration: "1:34:27",
    date: "13 marzo 2026",
    title: "Studio Serie A — 29ª Giornata",
    text: "Analisi completa della 29ª giornata di Serie A con pronostici e discussioni sui risultati più importanti.",
    url: "https://www.youtube.com/watch?v=b0xDcw9mYNM",
  },
  {
    id: "ep2",
    platform: "Twitch",
    type: "link",
    duration: "2:15:00",
    date: "12 marzo 2026",
    title: "Live Twitch — Pronostici Weekend",
    text: "Diretta su Twitch con pronostici, analisi pre-partita e interazione con la chat.",
    url: "https://www.twitch.tv/videos/2721343286",
  },
  {
    id: "ep3",
    platform: "TikTok",
    type: "link",
    duration: "0:45",
    date: "11 marzo 2026",
    title: "Clip TikTok — Momenti Migliori",
    text: "I momenti più divertenti e le perle di saggezza del nostro team.",
    url: "https://www.tiktok.com/@unoxdue_",
  },
];

// Il team — tre tipster e un host. Foto verificate.
export const hosts = [
  {
    id: "sono-micuccio",
    slug: "sono-micuccio",
    nickname: "Sono Micuccio",
    badge: "Il pioniere",
    role: "Fondatore & analista",
    photo: "/hosts/host2.jpg",
    isHost: false,
    bio: "Fondatore del progetto Aperiquattro. Pioniere nell'analisi dei campionati minori, si distingue per le sue analisi avanzate sui palinsesti sportivi, sempre fuori dagli schemi e ad alto potenziale.",
    instagram: "https://www.instagram.com/sonomicuccioreal/",
  },
  {
    id: "il-ninja",
    slug: "il-ninja",
    nickname: "Il Ninja",
    badge: "Lo specialista",
    role: "Specialista basket",
    photo: "/hosts/host3.jpg",
    isHost: false,
    bio: "Specialista del basket: quando c'è un tiro libero decisivo, è sempre pronto a colpire. Segue le gare fino all'alba senza mai perdere un colpo. Precisione, dedizione e un fiuto infallibile.",
    instagram: "https://www.instagram.com/ilniinja/",
  },
  {
    id: "il-marziano",
    slug: "il-marziano",
    nickname: "Il Marziano",
    badge: "Il veterano",
    role: "Tipster veterano",
    photo: "/hosts/host1.jpg",
    isHost: false,
    bio: "Figura storica nel panorama dei tipster italiani. Le sue giocate si distinguono per precisione e competenza, sempre accompagnate dal suo marchio di fabbrica: gli iconici Shooters.",
    instagram: "https://www.instagram.com/il.marziano_/",
  },
  {
    id: "antonello-santopaolo",
    slug: "antonello-santopaolo",
    nickname: "Antonello Santopaolo",
    badge: "La voce di UnoXdue",
    role: "Host",
    photo: "/team/antonello.jpg",
    isHost: true,
    bio: "Web content writer e moderatore di eventi, Antonello Santopaolo conduce e coordina le conversazioni di UnoXdue. Da anni opera nella comunicazione digitale, realizzando interviste e approfondimenti con professionisti e personalità del panorama italiano. È la voce che tiene insieme il podcast, anche quando preferisce restare fuori dall'inquadratura.",
    instagram: null,
  },
];

// Parlano di Noi — rassegna stampa
export const press = [
  {
    id: "calabria7",
    source: "Calabria 7",
    date: "24 Giugno 2026",
    title:
      "Ceravolo, 130 gol in carriera e l'orgoglio calabrese: «La mia terra è meravigliosa ma difficile»",
    excerpt:
      "Ospite del podcast UnoXdue, Fabio Ceravolo ripercorre i passaggi più significativi della sua carriera, dal legame con la Calabria alla storica promozione con il Benevento.",
    url: "https://calabria7.news/sport-vari/ceravolo-130-gol-in-carriera-e-lorgoglio-calabrese-la-mia-terra-e-meravigliosa-ma-difficile-li-nessuno-ti-regala-niente/",
  },
  {
    id: "cosenzachannel",
    source: "Cosenza Channel",
    date: "5 Giugno 2026",
    title:
      "Baclet ricorda i playoff col Cosenza: «Avremmo vinto anche contro la Juventus»",
    excerpt:
      "L'ex attaccante francese, ospite del podcast UnoXdue, racconta la cavalcata che riportò i lupi in Serie B dopo 15 anni di attesa.",
    url: "https://www.cosenzachannel.it/calcio/cosenza-calcio/baclet-ricorda-i-playoff-col-cosenza-avremmo-vinto-anche-contro-la-juventus-rr06av0s",
  },
  {
    id: "lacnews24",
    source: "LaC News24",
    date: "5 Giugno 2026",
    title:
      "Baclet ricorda i playoff col Cosenza: «Avremmo vinto anche contro la Juventus»",
    excerpt:
      "L'intervista di UnoXdue ad Allan Baclet rilanciata da LaC News24: i ricordi della promozione e il gruppo che scrisse la storia rossoblù.",
    url: "https://www.lacnews24.it/sport/baclet-ricorda-i-playoff-col-cosenza-avremmo-vinto-anche-contro-la-juventus-rr06av0s",
  },
];


// Pronostici — schedina di esempio (mock) ricreata con il brand UnoXdue.
// IMPORTANTE: nessun importo, bonus, vincita o branding di operatori.
// I pronostici sono opinioni editoriali. 18+ — Gioca responsabilmente.
export const predictionsMeta = {
  competition: "Serie A",
  season: "2025-2026",
  round: 38,
  title: "Pronostici Serie A — 38ª giornata",
  intro:
    "Le giocate del nostro team per l'ultima giornata di Serie A. Quote indicative al momento della pubblicazione: possono variare.",
  updatedAt: "21/05/2026 12:20",
};

export const predictions = [
  {
    id: "marziano-g38",
    tipsterId: "il-marziano",
    tipster: "Il Marziano",
    photo: "/hosts/host1.jpg",
    type: "Multipla",
    status: "In corso",
    totalOdds: "17.63",
    selections: [
      { competition: "Serie A", date: "22/05 · 20:45", match: "Fiorentina - Atalanta", market: "Multigol 2-4", pick: "Sì", odds: "1.49" },
      { competition: "Serie A", date: "23/05 · 20:45", match: "Lazio - Pisa", market: "Multigol 1-2 (1°T)", pick: "Sì", odds: "1.55" },
      { competition: "Serie A", date: "24/05 · 18:00", match: "Napoli - Udinese", market: "1X2 + U/O 3,5", pick: "1 + Under", odds: "2.09" },
      { competition: "Serie A", date: "24/05 · 20:45", match: "Lecce - Genoa", market: "Multigol Casa 1-3", pick: "Sì", odds: "1.35" },
      { competition: "Serie A", date: "24/05 · 20:45", match: "Cremonese - Como", market: "Goal/No Goal", pick: "Goal", odds: "1.78" },
      { competition: "Serie A", date: "24/05 · 20:45", match: "Verona - Roma", market: "1X2 + U/O 1,5", pick: "2 + Over", odds: "1.52" },
    ],
  },
  {
    id: "micuccio-g38",
    tipsterId: "sono-micuccio",
    tipster: "Sono Micuccio",
    photo: "/hosts/host2.jpg",
    type: "Multipla",
    status: "In corso",
    totalOdds: "6.42",
    selections: [
      { competition: "Serie A", date: "24/05 · 20:45", match: "Inter - Torino", market: "1X2", pick: "1", odds: "1.40" },
      { competition: "Serie A", date: "23/05 · 18:00", match: "Bologna - Sassuolo", market: "Over 2,5", pick: "Over", odds: "1.72" },
      { competition: "Serie A", date: "24/05 · 20:45", match: "Juventus - Milan", market: "Goal/No Goal", pick: "Goal", odds: "1.70" },
    ],
  },
  {
    id: "ninja-g38",
    tipsterId: "il-ninja",
    tipster: "Il Ninja",
    photo: "/hosts/host3.jpg",
    type: "Multipla",
    status: "In corso",
    totalOdds: "4.18",
    selections: [
      { competition: "Serie A", date: "24/05 · 20:45", match: "Atalanta - Parma", market: "1X2", pick: "1", odds: "1.45" },
      { competition: "Serie A", date: "23/05 · 20:45", match: "Roma - Empoli", market: "Multigol Casa 1-3", pick: "Sì", odds: "1.36" },
      { competition: "Serie A", date: "24/05 · 18:00", match: "Como - Cagliari", market: "Under 3,5", pick: "Under", odds: "2.12" },
    ],
  },
];
