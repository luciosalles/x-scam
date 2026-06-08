# Local Dashboard and Alert Database

Este dashboard e o centro minimo de operacao do MVP.

## O que ele resolve

| Problema | Solucao |
| --- | --- |
| Quero saber se o sistema esta vivo | Abra a Home e veja `Macro Monitor` e `Main Alert` |
| Quero ver historico dos alertas | Use a tabela `Alert History` |
| Quero filtrar noticia ou mercado | Use `type`, `level/regime` e busca |
| Quero saber se uma fonte quebrou | Abra `Status Dev` |
| Quero abrir a noticia sem sair do painel | Use o preview lateral |

## Como iniciar

No PowerShell, dentro do projeto:

```powershell
.\scripts\start-alert-dedupe-service.ps1
```

Se retornar:

```json
{"ok": true}
```

o servico esta rodando.

## Onde abrir

Dashboard:

```text
http://127.0.0.1:8787/dashboard
```

Status tecnico:

```text
http://127.0.0.1:8787/dashboard/status
```

API de alertas:

```text
http://127.0.0.1:8787/api/alerts
```

API de fontes:

```text
http://127.0.0.1:8787/api/source-health
```

API do overview macro:

```text
http://127.0.0.1:8787/api/overview
```

API do RTD:

```text
http://127.0.0.1:8787/api/rtd/overview
```

## Banco local

Arquivo:

```text
data/alerts.sqlite
```

Tabelas:

| Tabela | Uso |
| --- | --- |
| `sent_alerts` | dedupe de noticias para nao repetir a mesma headline |
| `alert_events` | historico de alertas exibido no dashboard |
| `source_checks` | ultimo health check das fontes |

## O que a Home mostra hoje

- alerta principal
- `Macro Monitor`
  - interno: `PTAX USD`, `Selic 2026`, `IPCA 2026`, `Cambio 2026`
  - externo: `ES`, `NQ`, `Gold`, `DXY`
- vies traduzido para leitura de `WIN`
- feed curto de alertas recentes

## O que a pagina RTD mostra

- estado do coletor `Profit RTD`
- buffer atual
- bias microestrutural simples
- simbolos monitorados
- ticks recentes
- plot salvo pelo coletor quando existir

## Atualizacao automatica

- bloco externo: atualiza rapido
- bloco interno: atualiza mais devagar
- a pagina nao precisa recarregar inteira para atualizar esses cards

## Preview lateral e links

- o titulo do alerta pode abrir a noticia em nova aba
- o campo `Fonte` pode abrir a noticia quando houver link
- o icone de preview abre a noticia em uma lateral dentro do proprio dashboard
- clicar na linha do alerta muda o alerta principal

## Como os workflows gravam

| Workflow | Node que grava | Endpoint |
| --- | --- | --- |
| `PROD - Trump Tariff Alert` | `Record News Alert` | `POST /api/alerts` |
| `PROD - Market Reaction Engine` | `Record Market Alert` | `POST /api/alerts` |
| `PROD - Brazil Local Alert` | `Record Brazil Local Alert` | `POST /api/alerts` |
| `PROD - BCB Direct Macro` | `Record BCB Direct Alert` | `POST /api/alerts` |

## Fontes Brasil Local

As fontes RSS.app reais ficam em:

```text
config/brazil_local_rss_app_urls.json
```

Quando uma fonte estiver com `enabled: true`, ela entra no health check do dashboard.

Para testar fora do dashboard:

```powershell
.\scripts\validate-brazil-local-rss.ps1
```

## Como interpretar

| Situacao | Interpretacao |
| --- | --- |
| Workflow executou, mas dashboard nao mudou | O filtro bloqueou ou o alerta nao chegou ao node `Record ... Alert` |
| Telegram/Discord enviou, mas dashboard nao gravou | Verifique `Record News Alert` ou `Record Market Alert` |
| Source Health `ok` | Fonte respondeu HTTP e conteudo basico parece valido |
| Source Health `error` | Fonte fora, bloqueio, rede ou URL ruim |
| Source Health `bad_content` | A fonte respondeu, mas pode ter entregue HTML ou conteudo inesperado |
| Macro card com ponto vermelho | dado antigo ou sem atualizacao recente |
| Macro card com ponto verde | dado considerado fresco dentro da regra da tela |

## Teste seguro

Para testar o banco sem acionar Telegram/Discord:

```powershell
$payload = @{
  alert_type = "test"
  level = "TEST"
  regime = "TEST"
  score = 1
  title = "Dashboard DB smoke test"
  source = "local"
  tendency = "teste controlado"
  conviction = "baixa"
  win_read = "sem leitura real"
  dollar_read = "sem leitura real"
  us_read = "sem leitura real"
  reason = "validar banco e dashboard"
  channels = @("dashboard")
} | ConvertTo-Json -Compress

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8787/api/alerts -Body $payload -ContentType "application/json"
```

Depois abra:

```text
http://127.0.0.1:8787/dashboard
```

## Regra operacional

Antes de vender ou ativar para grupos:

1. Deixe o dashboard aberto.
2. Confirme Home e `Status Dev` coerentes.
3. Confirme que alertas reais aparecem em `Alert History`.
4. Confirme que Telegram e Discord recebem a mesma leitura.
5. Ajuste thresholds somente depois de olhar o historico.
6. Para BCB direto, valide se PTAX e Expectativas mudaram antes de interpretar o alerta como novo.
