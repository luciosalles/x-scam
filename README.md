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
- `docs/setup-rss-app-n8n.md`: passo a passo operacional
- `docs/market-reaction-engine.md`: regras do fluxo de confirmacao de mercado
- `scripts/score-event.js`: simulador local para calibrar score antes de automatizar

## Primeiro MVP

1. Crie os feeds no RSS.app usando as URLs de `config/feed_layers.json`.
2. Importe `workflows/n8n-trump-tariff-alert-starter.json` no n8n.
3. Configure as credenciais de IA e Telegram.
4. Teste com sensibilidade `balanced`.
5. So depois de 24-48h de logs, aumente para `aggressive`.

## Produto

Venda como "market bias alert", nao como previsao garantida. O texto do alerta deve indicar viés e confianca, por exemplo:

```text
RED ALERT | Tariff headline detected
Bias: risk-off / NAS100 downside pressure
Confidence: 82%
Reason: White House + USTR mention tariff action against China.
```
