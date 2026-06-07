# Setup RSS.app + n8n

Fonte de verdade operacional:
- [Alert Map](C:/Users/scorpion/Documents/X-Scam/docs/alert-map.md)

## 1. Criar feeds no RSS.app

Comece pelas fontes da camada `official_primary` em `config/feed_layers.json`.

Prioridade do primeiro dia:

1. White House - Presidential Actions
2. White House - Briefing Room
3. USTR - Press Office
4. Federal Register - tariff search
5. Treasury - Press Releases
6. OFAC - Recent Actions
7. Reuters Markets
8. CNBC Markets

No RSS.app, para cada fonte:

1. Cole a URL principal.
2. Gere o feed.
3. Ative atualizacao rapida, se o plano permitir.
4. Copie a URL RSS gerada.
5. Substitua ou acrescente a URL no workflow n8n.

### Brasil Local primeiro

Para a camada Brasil Local, use `config/brazil_local_rss_app_seed_list.csv`.
Depois de gerar cada RSS no RSS.app, registre a URL real em `config/brazil_local_rss_app_urls.json`.
Se estiver confuso sobre qual fonte tentar primeiro, siga `docs/brazil-local-source-ladder.md`.

Ordem sugerida inicial:

1. Tesouro Nacional - Noticias
2. IBGE - Releases gerais
3. Petrobras - Agencia de Noticias
4. Vale - Informacoes para o mercado
5. IBGE - Tag IPCA
6. Tesouro Nacional - RTN
7. BCB - Comunicados do Copom
8. BCB - Atas do Copom
9. BCB - Calendario do BC
10. Ministério da Fazenda - Noticias

Para cada página:

1. Copie a URL oficial da página.
2. Cole no RSS.app.
3. Gere o feed.
4. Salve em `My Feeds`.
5. Copie a URL RSS gerada.
6. Cole em `config/brazil_local_rss_app_urls.json`, no campo `rss_url`.
7. Troque `enabled` para `true` apenas depois de validar.
8. Rode:

```powershell
.\scripts\validate-brazil-local-rss.ps1
```

9. Se o status for `ok`, cole a mesma URL no node `Brazil Local Feeds` do n8n, campo `feedUrl`.
10. Se a fonte falhar, nao insista nela. Passe para a seguinte da `source ladder`.

Observação:
- páginas muito dinâmicas podem exigir o `RSS Builder` em vez do gerador simples.
- RSS.app documenta duas opções: gerar direto por URL ou usar o Builder quando a página exigir seleção manual.
- O workflow `PROD - Brazil Local Alert` nao dispara erro se nenhum `feedUrl` estiver preenchido. Ele simplesmente nao envia nada.
- O node `Manual Test Trigger` continua servindo para smoke test sem depender de RSS.app.

Runbook completo:

```text
docs/brazil-local-rss-app-20-step-runbook.md
```

## 2. Google Alerts

Crie alertas com entrega por RSS quando disponivel, ou email se RSS nao aparecer.

Queries recomendadas:

```text
"Trump" "tariff" "China"
"Trump" "tariff" "Mexico"
"White House" "tariff"
"USTR" "Section 301"
"reciprocal tariffs"
"import duties" "China"
"tariff exemption"
"semiconductors" "tariff"
"autos" "tariff"
"steel aluminum tariffs"
```

## 3. n8n

Fluxos atuais:

1. `TEST - Telegram Smoke Test`: use primeiro. Se ele falhar, corrija Telegram antes de mexer em feeds.
2. `PROD - Trump Tariff Alert`: fluxo principal de noticias.
3. `PROD - Market Reaction Engine`: confirmacao por mercado.

Fluxo minimo de noticias:

1. Schedule Trigger a cada 1-5 minutos.
2. RSS Read para cada feed.
3. Merge.
4. Code node para normalizar titulo, fonte, data e link.
5. Code node para scoring inicial.
6. IA para classificacao final usando `prompts/impact_classifier.md`.
7. IF por `alert_level`.
8. Telegram apenas para alertas extremos no MVP.
9. WhatsApp apenas para `RED`, em etapa futura.
10. Google Sheets/Postgres para log e calibracao, em etapa futura.

## 4. Leitura de status

- Se todos os nodes ficam verdes e o Telegram nao dispara, o filtro bloqueou corretamente.
- Se o Telegram falha, cheque a credencial `Telegram account 2` e o `chat_id`.
- Se `RSS Read` falha, o problema esta no feed.
- Se o workflow esta `Active`, ele roda sozinho pelo schedule.
- Se voce clica `Execute workflow`, e apenas teste manual.
- O fluxo de noticias tem cooldown global de 30 minutos para evitar rajadas de alertas.
- O fluxo de noticias roda a cada 30 minutos; o fluxo de mercado roda a cada 30 segundos.

## 5. Sensibilidade

Use `balanced` no comeco.

- `conservative`: menos ruido, melhor para cliente pagante.
- `balanced`: bom para MVP e validacao.
- `aggressive`: bom para pesquisa, mas gera falsos positivos.

### Brasil Local

Para `Brasil Local`, comece com:

- `Mais conservador`: `RED` apenas
- `Equilibrado`: `Laranja` + `Vermelho`
- `Mais agressivo`: `Amarelo` + `Laranja` + `Vermelho`

Sugestão inicial:

- `Laranja` quando a tese local ficar clara, mas ainda precisar de confirmação
- `Vermelho` quando `DI`, `dólar`, `Copom`, `IPCA`, `Petrobras` ou `Vale` baterem juntos

## 6. Calibracao

Durante 48 horas, registre:

- headline
- fonte
- score calculado
- score da IA
- alerta enviado
- movimento em NAS100/SPX/DXY/Gold nos 5, 15 e 60 minutos seguintes
- se o alerta teria sido util ou ruidoso

Depois ajuste:

- peso da fonte
- pesos de palavras
- threshold de `ORANGE` e `RED`
- cooldown de duplicados

Para o Brasil Local, acompanhe especificamente:

- `DI` e `dólar`
- `Copom` e `IPCA`
- `Tesouro` e `Fazenda`
- `Petrobras` e `Vale`
- reação do `WIN` na abertura e na primeira hora
