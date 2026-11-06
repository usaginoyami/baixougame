// Jogos do calendário de lançamentos (página /lancamentos/).
// Para adicionar um jogo, copie uma linha e mude os campos:
//   data        "AAAA-MM-DD"
//   titulo      nome do jogo
//   plataformas lista: "PC", "PS5", "Xbox", "Switch", "Switch 2"
//   tag         texto da etiqueta ("Lançamento", "Acesso antecipado"...)
//   incerto     true quando a data ainda não é firme (etiqueta amarela)
//   destaque    true em UM jogo para o aviso com contagem regressiva no topo
// Datas coletadas de calendários públicos em 06/11/2026; confira antes de publicar.

window.LANCAMENTOS_CONFIG = {
  // Para onde o botão "Seguir preço" leva: a busca da página inicial.
  linkPreco: function (titulo) {
    return "../?q=" + encodeURIComponent(titulo);
  }
};

window.LANCAMENTOS = [
  { data: "2026-11-02", titulo: "Gravhounds", plataformas: ["PC", "Xbox"], tag: "Acesso antecipado" },
  { data: "2026-11-12", titulo: "Metaphor: ReFantazio", plataformas: ["Switch 2"], tag: "Chega ao Switch 2" },
  { data: "2026-11-19", titulo: "Grand Theft Auto VI", plataformas: ["PS5", "Xbox"], tag: "Lançamento", destaque: true },

  { data: "2026-12-03", titulo: "Dragon Quest Monsters: The Withered World", plataformas: ["PC", "PS5", "Xbox", "Switch", "Switch 2"], tag: "Lançamento" },
  { data: "2026-12-03", titulo: "Xenoblade Chronicles 3", plataformas: ["Switch 2"], tag: "Switch 2 Edition" },

  { data: "2027-01-14", titulo: "Danganronpa 2×2", plataformas: ["PC", "PS5", "Xbox", "Switch", "Switch 2"], tag: "Lançamento" },
  { data: "2027-01-15", titulo: "Stranger Than Heaven", plataformas: ["PC", "PS5", "Xbox"], tag: "Lançamento" },
  { data: "2027-01-21", titulo: "Wandering Sword", plataformas: ["Switch", "Switch 2"], tag: "Lançamento" },
  { data: "2027-01-28", titulo: "Metroid Ravenous", plataformas: ["Switch 2"], tag: "Lançamento" },
  { data: "2027-01-28", titulo: "Tropico 7", plataformas: ["PC", "PS5", "Xbox"], tag: "Lançamento" },

  { data: "2027-02-04", titulo: "Metro 2039", plataformas: ["PC", "PS5", "Xbox"], tag: "Data varia entre fontes", incerto: true },
  { data: "2027-02-12", titulo: "Tomb Raider: Legacy of Atlantis", plataformas: ["PC", "PS5", "Switch 2"], tag: "Data a confirmar", incerto: true },
  { data: "2027-02-18", titulo: "Persona 4 Revival", plataformas: ["PC", "PS5", "Xbox"], tag: "Lançamento" },
  { data: "2027-02-23", titulo: "Fable", plataformas: ["PC", "PS5", "Xbox"], tag: "Lançamento" }
];
