# Local Dashboard and Alert Database

Este dashboard e o centro minimo de operacao do MVP.

## O que ele resolve

| Problema | Solucao |
| --- | --- |
| Quero saber se o sistema esta vivo | Abra o dashboard e veja `Source Health` |
| Quero ver historico dos alertas | Use a tabela `Alert History` |
| Quero filtrar noticia ou mercado | Use `type`, `level/regime` e busca |
| Quero saber se uma fonte quebrou | Clique em `Check Sources` |

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

API de alertas:

```text
http://127.0.0.1:8787/api/alerts
```

API de fontes:

```text
http://127.0.0.1:8787/api/source-health
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

## Como os workflows gravam

| Workflow | Node que grava | Endpoint |
| --- | --- | --- |
| `PROD - Trump Tariff Alert` | `Record News Alert` | `POST /api/alerts` |
| `PROD - Market Reaction Engine` | `Record Market Alert` | `POST /api/alerts` |
| `PROD - Brazil Local Alert` | `Record Brazil Local Alert` | `POST /api/alerts` |

## Fontes Brasil Local

As fontes RSS.app reais ficam em:

```text
config/brazil_local_rss_app_urls.json
```

Quando uma fonte estiver com `enabled: true`, ela entra no health check do dashboard depois de clicar em `Checar fontes`.

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
2. Confirme `Source Health` verde.
3. Confirme que alertas reais aparecem em `Alert History`.
4. Confirme que Telegram e Discord recebem a mesma leitura.
5. Ajuste thresholds somente depois de olhar o historico.
