# Trump Tariff Alert System

Sistema rapido de monitoramento para headlines politicas/economicas com foco em tarifas, comercio global e impacto intraday em ativos de risco.

O projeto foi montado para funcionar primeiro como operacao no-code/low-code:

- RSS.app ou feeds nativos para capturar fontes
- n8n para orquestrar coleta, IA e alertas
- Grok, Claude ou OpenAI para classificar impacto
- Telegram/WhatsApp para distribuicao
- Configuracoes versionadas em `config/`

## Estrutura

- `config/feed_layers.json`: fontes separadas por confiabilidade e funcao
- `config/alert_policy.json`: niveis de alerta, sensibilidade, palavras-chave e scoring
- `prompts/impact_classifier.md`: prompt de IA para transformar noticia em alerta util
- `workflows/n8n-trump-tariff-alert-starter.json`: workflow base importavel no n8n
- `workflows/n8n-market-reaction-engine-starter.json`: workflow separado para ES/NQ/DXY/Gold
- `workflows/n8n-brazil-local-alert-starter.json`: scaffold da camada Brasil Local
- `workflows/n8n-telegram-smoke-test.json`: teste simples para validar Telegram e `chat_id`
- `config/brazil_local_feed_layers.json`: camada Brasil Local pronta para RSS.app e n8n
- `config/brazil_local_rss_app_seed_list.csv`: lista pratica para gerar RSS.app do Brasil Local
- `config/brazil_local_rss_app_urls.json`: onde colar as URLs RSS reais geradas no RSS.app
- `docs/setup-rss-app-n8n.md`: passo a passo operacional
- `docs/brazil-local-rss-app-20-step-runbook.md`: roteiro de 20 etapas para ligar Brasil Local real
- `docs/technical-operation-manual.md`: manual tecnico de execucao e configuracao
- `docs/project-status.md`: estado atual, pendencias e prioridades
- `docs/market-reaction-engine.md`: regras do fluxo de confirmacao de mercado
- `docs/dashboard.md`: banco local, historico, filtros e health check das fontes
- `scripts/score-event.js`: simulador local para calibrar score antes de automatizar

## Operacao atual

Existem 3 workflows no n8n:

1. `TEST - Telegram Smoke Test`: envia uma mensagem falsa unica. Use para provar que Telegram funciona.
2. `PROD - Trump Tariff Alert`: monitora noticias de tarifas e envia apenas alertas extremos.
3. `PROD - Market Reaction Engine`: monitora ES/NQ/DXY/Gold e envia apenas confluencia forte.
4. `PROD - Brazil Local Alert`: scaffold para Copom, IPCA, fiscal, Petrobras e Vale.

Como interpretar:

- Workflow verde sem Telegram: funcionou, mas o filtro bloqueou por nao ser forte o bastante.
- Erro no node Telegram: problema de credencial/chat_id.
- Erro no node RSS/HTTP: problema de fonte/feed/rede.
- `Active` ligado: roda sozinho pelo schedule.
- `Execute workflow`: teste manual.

## Live

Os workflows de producao rodam em cadencias diferentes:

- noticia: a cada 30 minutos, com `preScore >= 170`
- mercado: a cada 30 segundos, com `score >= 100`
- cooldown de noticia: 30 minutos
- cooldown do mercado: 30 minutos
- Brasil Local: começar com `Laranja` acima de `70` e `Vermelho` acima de `85`

Para reiniciar o n8n usando o perfil certo:

```powershell
.\scripts\start-n8n.ps1
```

Para iniciar o banco local, dedupe, dashboard e health check:

```powershell
.\scripts\start-alert-dedupe-service.ps1
```

Dashboard local:

```text
http://127.0.0.1:8787/dashboard
```

Para validar as URLs RSS.app do Brasil Local antes de ligar no n8n:

```powershell
.\scripts\validate-brazil-local-rss.ps1
```

Para rodar um stress test tecnico minimo:

```powershell
.\scripts\run-stress-test.ps1
```

Para reimportar os 3 workflows:

```powershell
.\scripts\import-workflow.ps1
```

Observacao: reimportar workflows pode voltar `active` para `false`. Depois de importar, confira no n8n quais workflows devem ficar ligados.

## Primeiro MVP

1. Crie os feeds no RSS.app usando as URLs de `config/feed_layers.json`.
2. Rode `TEST - Telegram Smoke Test`.
3. Rode manualmente os dois workflows `PROD`.
4. Ative primeiro `PROD - Trump Tariff Alert`.
5. Ative `PROD - Market Reaction Engine` depois que Stooq responder sem erro.
6. So depois de 24-48h de logs, aumente a complexidade.

## Brasil Local

O workflow `PROD - Brazil Local Alert` tem dois modos:

- `Manual Test Trigger`: envia um alerta falso controlado para provar Telegram e dashboard.
- `Every 10 Minutes`: usa as URLs RSS.app coladas no node `Brazil Local Feeds`.

Enquanto os campos `feedUrl` estiverem vazios, o schedule roda sem enviar nada. Isso e esperado.

## Produto

Venda como "market bias alert", nao como previsao garantida. O texto do alerta deve indicar viés e confianca, por exemplo:

```text
RED | TARIFF ALERT
Titulo: ...
Tendencia: baixa
Conviccao: alta
WIN: ...
Dolar: ...
Nasdaq/ES: ...
```
