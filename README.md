# baixougame

Site estático que mostra preços de jogos de PC em reais, com histórico. Roda de graça no GitHub Pages e se atualiza sozinho pelo GitHub Actions.

## Como funciona

- `index.html` é o site inteiro (HTML, CSS e JS). Ele lê `data/games.json`.
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

Inclua uma linha em `data/watchlist.json`. O `appid` é o número na URL da página do jogo na Steam (`store.steampowered.com/app/<appid>/`).

## Links de afiliado (Nuuvem Co-Op)

A Nuuvem não oferece API nem feed público de preços, e os termos de uso dela proíbem coletar dados do site com robôs. Por isso o baixougame **não mostra preços da Nuuvem**. O que dá para fazer é um botão "Ver na Nuuvem" com o seu link de afiliado:

1. Entre no programa Nuuvem Co-Op (pela Rakuten) e espere a aprovação.
2. No painel de afiliado, crie o link do jogo.
3. Em `data/watchlist.json`, adicione o campo `links` no jogo:

```json
{"appid": 1145360, "name": "Hades", "links": {"nuuvem": "https://seu-link-de-afiliado"}}
```

4. Na próxima atualização (ou rodando o workflow na mão), o botão aparece na janela de detalhes do jogo e o aviso de links de afiliado aparece no rodapé.

Leia as regras do programa antes de divulgar os links.

## Adicionar outras lojas

O site já mostra várias lojas na tabela e no gráfico. Para somar uma loja:

1. Em `scripts/update_prices.py`, crie uma função parecida com `fetch_steam()` que devolva `{appid: {price, regular, cut, url}}`.
2. Chame essa função em `main()` e coloque o resultado em `stores["nome-da-loja"]`.
3. Registre o nome de exibição em `STORE_NAMES`.

Confira os termos de uso de cada loja antes de coletar os dados dela.

## Avisos

- O endereço de preços da Steam usado aqui (`store.steampowered.com/api/appdetails`) não é uma API oficial documentada. Ele pode mudar ou limitar requisições. O script já espera 2 segundos entre lotes.
- O script não foi testado contra a Steam de verdade neste ambiente, só contra uma resposta simulada. Rode o workflow uma vez e confira o resultado.
- O GitHub pode pausar workflows agendados de repositórios públicos sem atividade por 60 dias. Se isso acontecer, reative em Actions.
