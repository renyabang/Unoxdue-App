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
  { label: "Il Podcast", href: "#about" },
  { label: "Interviste", href: "#interviste" },
  { label: "Contenuti", href: "#contenuti" },
  { label: "Conduttori", href: "#conduttori" },
  { label: "Parlano di Noi", href: "#press" },
  { label: "Social", href: "#social" },
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
  "UnoXdue è il podcast calcistico dove analisi tattica, pronostici e dibattito appassionato si incontrano per offrirti uno sguardo unico sul mondo del calcio italiano.",
  "Ogni settimana, Sonomuiccio, Ninja e Marziano si ritrovano in diretta per discutere della Serie A, analizzare le partite più importanti e confrontarsi sui temi caldi del calcio italiano ed europeo.",
  "Dal pre-partita alle analisi post-gara, passando per il calciomercato, UnoXdue è il punto di ritrovo per tutti gli appassionati che cercano contenuti autentici e approfonditi.",
];

export const features = [
  {
    icon: "radio",
    title: "Dirette Settimanali",
    text: "Live su Twitch con analisi e dibattito in tempo reale.",
  },
  {
    icon: "target",
    title: "Focus Serie A",
    text: "Approfondimenti su tutte le partite del campionato italiano.",
  },
  {
    icon: "users",
    title: "Tre Conduttori",
    text: "Tre punti di vista diversi per un'analisi completa.",
  },
  {
    icon: "clapperboard",
    title: "Contenuti Multipli",
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
    text: "I momenti più divertenti e le perle di saggezza dei nostri conduttori.",
    url: "https://www.tiktok.com/@unoxdue_",
  },
];

// Conduttori — NB: le foto sono abbinate in ordine, da confermare/sistemare.
export const hosts = [
  {
    id: "sonomuiccio",
    nickname: "Sonomuiccio",
    realName: "Domenico Ruffa",
    badge: "Il Pioniere",
    role: "Fondatore & Analista",
    photo: "/hosts/host1.jpg",
    bio: "Fondatore del progetto Aperiquattro. Pioniere nell'analisi dei campionati minori, si distingue per le sue analisi avanzate sulle scommesse sportive, sempre fuori dagli schemi e ad alto potenziale.",
    instagram: "https://www.instagram.com/sonomicuccioreal/",
  },
  {
    id: "ninja",
    nickname: "Il Ninja",
    realName: "Antonio Nasta",
    badge: "Lo Specialista",
    role: "Specialista Basket",
    photo: "/hosts/host2.jpg",
    bio: "Lo specialista del Basket: quando c'è un tiro libero decisivo, è sempre pronto a colpire. Segue le gare fino all'alba senza mai perdere un colpo. Precisione, dedizione e un fiuto infallibile.",
    instagram: "https://www.instagram.com/ilniinja/",
  },
  {
    id: "marziano",
    nickname: "Il Marziano",
    realName: "Giuseppe Ruocco",
    badge: "Il Veterano",
    role: "Tipster Veterano",
    photo: "/hosts/host3.jpg",
    bio: "Figura storica nel panorama Tipster Italia. Le sue giocate si distinguono per precisione e competenza, sempre accompagnate dal suo marchio di fabbrica: gli iconici Shooters.",
    instagram: "https://www.instagram.com/il.marziano_/",
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
