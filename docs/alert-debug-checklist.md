# Alert Debug Checklist

Tabela curta para teste rapido e triagem.

## Checklist

| O que testar | Como saber se quebrou | Qual node olhar primeiro |
| --- | --- | --- |
| `TEST - Telegram Smoke Test` | Nenhuma mensagem chega no Telegram | `Telegram Smoke Alert` |
| `PROD - Trump Tariff Alert` | Workflow roda, mas nao envia nada em noticia claramente forte | `High Impact Only` |
| `PROD - Trump Tariff Alert` | Envia repetido a mesma noticia | `Persist Alert Log` |
| `PROD - Trump Tariff Alert` | Node fica vermelho com erro HTTP | `Check Alert Log` |
| `PROD - Market Reaction Engine` | Nao envia em dia util com mercado movendo forte | `Score Market Snapshot` |
| `PROD - Market Reaction Engine` | Envia spam com pequenas mudancas | `Score Market Snapshot` |
| `PROD - Market Reaction Engine` | Telegram dispara, mas Discord nao | `Discord Market Alert` |
| `PROD - Market Reaction Engine` | Fonte de mercado nao responde | `Fetch Market CSV` |
| Dashboard local | Nao abre `http://127.0.0.1:8787/dashboard` | `scripts/start-alert-dedupe-service.ps1` |
| Dashboard local | Abre, mas nao mostra alertas novos | `Record News Alert` ou `Record Market Alert` |
| Source Health | Fonte aparece `error` | `/api/source-health` e URL da fonte |

## Ordem de triagem

1. Validar se o `n8n` esta online.
2. Rodar o workflow manualmente.
3. Verificar o primeiro node que ficou vermelho.
4. Conferir se o problema e de fonte, score, dedupe ou canal.
5. Abrir `http://127.0.0.1:8787/dashboard` para confirmar historico e health check.
6. Atualizar `docs/alert-map.md` se a regra de produto mudou.
