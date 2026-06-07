# Brazil Local Source Ladder

Use esta ordem. Nao tente todas de uma vez.

## Nivel 1: tentar primeiro

1. `IBGE - Releases gerais`
2. `IBGE - Tag IPCA`
3. `BCB - Comunicados do Copom`
4. `BCB - Atas do Copom`
5. `BCB - Calendario do BC`
6. `UOL Economia`
7. `UOL - Ultimas de Economia`
8. `UOL - Investimentos / Bolsas e Acoes`

Essas fontes ja possuem melhor chance de feed oficial ou fluxo direto e tendem a ser as melhores para validar a infraestrutura.

## Nivel 2: depois

1. `Tesouro Nacional - Noticias`
2. `Tesouro Nacional - RTN`
3. `Ministerio da Fazenda - Noticias`
4. `Petrobras - Agencia de Noticias`
5. `Vale - Informacoes para o mercado`
6. `Vale - Press Releases`

## Nivel 3: opcional e mais chato

1. `B3 - Futuro de Ibovespa`
2. `B3 - Mercado Futuro`
3. `B3 - DI1 / Juros`
4. `B3 - Mini Dolar`
5. `B3 - Dolar Comercial futuro`
6. `B3 - VIX Brasil`

## Regra de trabalho

- Escolha uma fonte.
- Gere o RSS no RSS.app.
- Valide a URL.
- So depois passe para a proxima.

## Como saber que a fonte vale a pena

- O RSS.app conseguiu gerar feed sem erro.
- O feed mostra itens recentes.
- O `.\scripts\validate-brazil-local-rss.ps1` mostra `ok`.
- O node `Brazil Local Feeds` no n8n recebe a mesma URL e roda sem erro.

## O que fazer se falhar

- Se o `RSS Generator` falhar, tente `RSS Builder`.
- Se o `RSS Builder` ficar confuso, pule para a proxima fonte da lista.
- Se a fonte nao gerar RSS de forma razoavel, nao force. Use outra.
- Se existir RSS oficial, prefira ele sempre.
