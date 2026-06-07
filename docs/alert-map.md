# Alert Map

Este documento e a fonte de verdade operacional do projeto.

Atualize sempre que mudar:
- feeds
- thresholds
- canais
- dedupe
- regras de regime

## Visao Geral

| Alert | Objetivo | Fontes | Saida | Status |
| --- | --- | --- | --- | --- |
| `TEST - Telegram Smoke Test` | Validar Telegram, chat_id e credencial | Nenhuma | Telegram | Teste manual |
| `PROD - Trump Tariff Alert` | Detectar noticias de tarifa, comercio e choque macro | Google News / fontes tematicas | Telegram, futuro Discord | Produção |
| `PROD - Market Reaction Engine` | Detectar regime de mercado e confluencia risk-off / risk-on | Yahoo Finance chart endpoint, Stooq fallback | Telegram, Discord webhook | Produção |

## News Alert

| Camada | Fonte | Uso | Observacao |
| --- | --- | --- | --- |
| `primary` | Google News query: Trump tariff China | Alta prioridade | Gera sinais de tarifa e China |
| `primary` | Google News query: USTR Section 301 tariff | Alta prioridade | Ponto oficial / regulatorio |
| `primary` | Google News query: White House tariff Mexico | Alta prioridade | Ruido de politica publica com impacto direto |
| `primary` | Google News query: tariff exemption | Alta prioridade | Pode gerar alivio / reversao |
| `secondary` | Google News query: Trump trade Brazil | Media prioridade | Inclui Brasil no mapa de impacto |
| `secondary` | Google News query: Trump trade Mexico | Media prioridade | Complementa a camada principal |
| `secondary` | Google News query: Trump trade Canada | Media prioridade | Complementa a camada principal |
| `secondary` | Google News query: US China trade tariff | Media prioridade | Enquadra guerra comercial |
| `sector` | Google News query: Section 232 steel tariff | Setorial | Afecta acoes e commodities |
| `sector` | Google News query: semiconductor tariff trade | Setorial | Impacto em tech / supply chain |
| `sector` | Google News query: auto tariff Trump | Setorial | Impacto em autos / industriais |
| `sector` | Google News query: export restrictions trade US | Setorial | Contexto de oferta / comercio |

## Market Reaction

| Ativo | Label | Fonte principal | Fonte fallback | Uso |
| --- | --- | --- | --- | --- |
| `ES=F` | `ES` | Yahoo Finance chart | Stooq | S&P futuro / risco global |
| `NQ=F` | `NQ` | Yahoo Finance chart | Stooq | Nasdaq / growth risk |
| `GC=F` | `Gold` | Yahoo Finance chart | Stooq | safe haven / stress |
| `DX-Y.NYB` | `DXY` | Yahoo Finance chart | Stooq | dolar / risk-off |

## Regras de Regime

| Regime | Condicao | Acao |
| --- | --- | --- |
| `RISK_OFF` | ES/NQ fracos e DXY/Gold confirmando | Enviar alerta |
| `RISK_ON` | ES/NQ fortes e DXY cedendo | Enviar alerta |
| `neutral` | Sem confluencia suficiente | Nao enviar |
| `reversal` | Mudanca de `RISK_OFF` para `RISK_ON` ou vice-versa | Enviar alerta |
| `material_worsening` | Mesmo regime com piora material do score | Enviar update |

## Thresholds

| Workflow | Threshold atual | Observacao |
| --- | --- | --- |
| `PROD - Trump Tariff Alert` | `preScore >= 100` | Pode gerar `YELLOW`, `ORANGE`, `RED` |
| `PROD - Market Reaction Engine` | `score >= 100` | Envia apenas quando ha regime forte |

## Dedupe

| Workflow | Tipo | Janela | Observacao |
| --- | --- | --- | --- |
| `PROD - Trump Tariff Alert` | Dedupe persistente local | 1 hora | Bloqueia repeticao da mesma noticia |
| `PROD - Market Reaction Engine` | Dedupe por regime | 10 minutos + delta de score | Bloqueia spam e libera update quando piora |

## Canais

| Canal | Uso | Status |
| --- | --- | --- |
| Telegram | Canal principal do MVP | Ativo |
| Discord | Segunda saida planejada | Preparado via `discordText` |

## Sensibilidade

| Perfil | Quando usar | Efeito |
| --- | --- | --- |
| `aggressive` | Pesquisa / teste | Mais volume, mais ruído |
| `balanced` | MVP | Melhor equilibrio |
| `conservative` | Produção paga | Menos ruído, mais qualidade |

## Fallback e Prioridade

| Ordem | Fonte | Regra |
| --- | --- | --- |
| 1 | Yahoo Finance | Fonte principal do market engine |
| 2 | Stooq | Fallback manual via `MARKET_DATA_SOURCE=stooq` |

## Notas Operacionais

- Se o mercado estiver fechado, o market engine pode não enviar alerta. Isso e normal.
- Se a fonte ficar silenciosa, primeiro valide a resposta HTTP, depois o parser, depois o threshold.
- Se o Telegram enviar, mas o Discord nao, o problema esta no webhook ou na variavel `DISCORD_WEBHOOK_URL`.

## Proxima Acao

Quando mudar algo neste projeto, atualize este arquivo antes de reimportar workflow.

## Diagnostico Rapido

- [Alert Debug Checklist](C:/Users/scorpion/Documents/X-Scam/docs/alert-debug-checklist.md)
- [Local Dashboard and Alert Database](C:/Users/scorpion/Documents/X-Scam/docs/dashboard.md)

## Dashboard e Banco Local

| Item | Valor |
| --- | --- |
| Dashboard | `http://127.0.0.1:8787/dashboard` |
| Banco | `data/alerts.sqlite` |
| Alert API | `POST /api/alerts` |
| Historico API | `GET /api/alerts` |
| Health API | `GET /api/source-health` |

## Gravacao de Historico

| Workflow | Node | O que grava |
| --- | --- | --- |
| `PROD - Trump Tariff Alert` | `Record News Alert` | noticias enviadas ao Telegram |
| `PROD - Market Reaction Engine` | `Record Market Alert` | regimes enviados ao Telegram/Discord |

Se Telegram ou Discord enviar, mas o dashboard nao registrar, investigue primeiro o node `Record News Alert` ou `Record Market Alert`.
