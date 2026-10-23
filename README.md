# baixougame

Site estático que mostra preços de jogos de PC em reais, com histórico. Roda de graça no GitHub Pages e se atualiza sozinho pelo GitHub Actions.

## Como funciona

- `index.html` (com `style.css`) é a página inicial. Ela lê `data/games.json`.
- `scripts/build_pages.py` gera uma página para cada jogo em `jogos/<nome-do-jogo>/`, mais o `sitemap.xml` e o `robots.txt`. Essas páginas e arquivos são gerados pelo robô: não edite à mão.
- `site.json` guarda o endereço do site e o medidor de visitas.
- `data/watchlist.json` é a lista de jogos acompanhados (`appid` da Steam e nome).
- `scripts/update_prices.py` consulta o preço de cada jogo na Steam Brasil e grava `data/games.json`. O histórico ganha uma linha nova só quando o preço muda.
- `.github/workflows/update-prices.yml` roda o script todo dia às 06:17 (Brasília) e salva o resultado no repositório.

O `data/games.json` que vem no projeto tem **dados de exemplo** (preços inventados). Na primeira atualização real, eles são descartados e o histórico começa do zero.

## Publicar

1. Crie um repositório no GitHub e envie esta pasta.
2. Em **Settings → Pages**, escolha a branch `main` e a pasta `/ (root)`.
3. Em **Actions**, abra "Atualizar preços" e clique em **Run workflow** para a primeira coleta.

Para testar no seu computador: `python scripts/update_prices.py` e depois `python -m http.server`, abrindo `http://localhost:8000`.

## Adicionar jogos

**Automático:** a cada execução o script olha as promoções em destaque da Steam Brasil (promoções, mais vendidos, oferta do dia) e cadastra em `data/discovered.json` os jogos com desconto grande que ainda não estão no site. Ele confere se é mesmo um jogo pago (DLC, trilha sonora e demo ficam de fora). Os jogos novos aparecem no site na mesma execução e entram no resumo do workflow na aba Actions.

Os limites ficam no topo de `scripts/update_prices.py`:

| Constante | Padrão | O que faz |
|---|---|---|
| `DISCOVER` | `True` | `False` desliga a descoberta |
| `MIN_DISCOUNT` | `50` | desconto mínimo (%) para cadastrar |
| `MAX_NEW_PER_RUN` | `10` | máximo de jogos novos por execução |
| `MAX_GAMES` | `300` | máximo total de jogos no site |

Para tirar um jogo descoberto e impedir que ele volte, coloque o `appid` dele em `data/ignored.json` (por exemplo `[1234567, 7654321]`). Na próxima execução ele sai do site.

**Manual, só com o nome (mais fácil):**

1. No GitHub, abra a aba **Actions** e clique em **Adicionar jogo**.
2. Clique em **Run workflow**, digite o nome do jogo (ou o link da Steam, ou o appid) e confirme. Para vários, separe com `;` (por exemplo `Hades; Celeste`).
3. Em cerca de um minuto o jogo aparece no site, com o nome oficial, a capa e o preço.

O script procura o jogo na Steam Brasil e confere que é mesmo um jogo (trilha sonora, DLC, demo e jogo gratuito ficam de fora). Se o nome bater com mais de um jogo, ele **não escolhe por você**: a execução termina em vermelho e o resumo (na página da execução) lista as opções com o appid de cada uma. Rode de novo com o appid ou com o nome exato. Se o jogo estava em `data/ignored.json`, ele sai de lá, porque você pediu.

Para usar no seu computador: `python scripts/add_game.py "Hades"` e depois `python scripts/update_prices.py`.

**Manual, editando o arquivo:** inclua uma linha em `data/watchlist.json`. O `appid` é o número na URL da página do jogo na Steam (`store.steampowered.com/app/<appid>/`). Essa lista é sua: o script só escreve nela quando você pede um jogo pelo "Adicionar jogo" (ou por `add_game.py`), e nunca apaga nada.

## Links de afiliado (Nuuvem e Green Man Gaming)

A Nuuvem não oferece API nem feed público de preços, e os termos de uso dela proíbem coletar dados do site com robôs. Os termos da Green Man Gaming exigem autorização escrita para uso comercial do site. Por isso o baixougame **não mostra preços dessas lojas**. O que dá para fazer é um botão "Ver na Nuuvem" ou "Ver na Green Man Gaming" com o seu link de afiliado:

1. Entre no programa de afiliados da loja e espere a aprovação: Nuuvem Co-Op (pela Rakuten) ou Green Man Gaming (pelo Impact).
2. No painel de afiliado, crie o link do jogo.
3. Em `data/watchlist.json`, adicione o campo `links` no jogo (`nuuvem` e/ou `gmg`):

```json
{"appid": 1145360, "name": "Hades", "links": {"nuuvem": "https://seu-link-da-nuuvem", "gmg": "https://seu-link-da-gmg"}}
```

4. Na próxima atualização (ou rodando o workflow na mão), o botão aparece na janela de detalhes do jogo e o aviso de links de afiliado aparece no rodapé.

Só os jogos de `data/watchlist.json` recebem botões. Para pôr link num jogo descoberto automaticamente, copie o `appid` e o nome dele de `data/discovered.json` para a `watchlist.json` e adicione o `links` lá.

Leia as regras de cada programa antes de divulgar os links.

## Páginas de cada jogo e Google

Cada jogo ganha um endereço próprio, como `.../baixougame/jogos/hades/`, com título, descrição e prévia de link (aparece ao compartilhar no WhatsApp, Discord etc.). O endereço de um jogo **nunca muda** depois de criado (fica salvo no campo `slug` de `data/games.json`).

Para o Google achar as páginas: abra o [Google Search Console](https://search.google.com/search-console), adicione `https://usaginoyami.github.io/baixougame/` como propriedade e envie o `sitemap.xml`. Se um dia você usar domínio próprio, troque o `url` em `site.json` e os endereços em `index.html` (canonical e `og:url`).

## Contador de visitas

O site não vem com contador ligado. Para ligar, escolha um serviço que não use cookies e que permita uso comercial no plano que você vai usar (confira os termos; alguns planos grátis são só para projetos sem fins lucrativos). Opções comuns: Cloudflare Web Analytics e Umami. Cada serviço dá um trecho de script. Coloque o endereço e os atributos dele em `site.json`:

```json
"analytics": {"src": "https://static.cloudflareinsights.com/beacon.min.js", "attrs": {"data-cf-beacon": "{\"token\": \"SEU_TOKEN\"}"}}
```

Só endereços `https://` são aceitos. Com o contador ligado, aparece um aviso no rodapé do site. Na próxima atualização as páginas dos jogos também passam a carregar o contador.

## Adicionar outras lojas

O site já mostra várias lojas na tabela e no gráfico. Para somar uma loja:

1. Em `scripts/update_prices.py`, crie uma função parecida com `fetch_steam()` que devolva `{appid: {price, regular, cut, url}}`.
2. Chame essa função em `main()` e coloque o resultado em `stores["nome-da-loja"]`.
3. Registre o nome de exibição em `STORE_NAMES`.

Confira os termos de uso de cada loja antes de coletar os dados dela.

## Avisos

- O endereço de preços da Steam usado aqui (`store.steampowered.com/api/appdetails`) não é uma API oficial documentada. Ele pode mudar ou limitar requisições. O script já espera 2 segundos entre lotes.
- A coleta de preços já rodou de verdade no seu GitHub. A descoberta de jogos foi testada só com respostas simuladas: rode o workflow uma vez e confira a seção "Jogos novos" no resumo da execução. Se a Steam mudar a vitrine, a descoberta falha sozinha e a coleta de preços continua normal.
- A vitrine da Steam mostra poucas promoções por vez (algumas dezenas). Os jogos novos entram aos poucos, conforme as promoções mudam ao longo dos dias.
- O GitHub pode pausar workflows agendados de repositórios públicos sem atividade por 60 dias. Se isso acontecer, reative em Actions.
