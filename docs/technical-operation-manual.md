# Manual Tecnico de Operacao

Este documento serve para subir, testar e operar o projeto sem depender de memoria da conversa.

## 1. O que existe hoje

- `TEST - Telegram Smoke Test`
- `PROD - Trump Tariff Alert`
- `PROD - Market Reaction Engine`
- `PROD - Brazil Local Alert`
- `PROD - BCB Direct Macro`

## 2. Como subir o ambiente local

No PowerShell, dentro da raiz do projeto:

```powershell
.\scripts\start-alert-dedupe-service.ps1
.\scripts\start-n8n.ps1
```

O dashboard local fica em:

```text
http://127.0.0.1:8787/dashboard
```

## 3. Como validar a base

```powershell
.\scripts\validate-brazil-local-rss.ps1
```

Use isso depois de colar URLs reais no arquivo:

```text
config/brazil_local_rss_app_urls.json
```

## 4. Ordem de teste

1. Rodar `TEST - Telegram Smoke Test`.
2. Rodar `PROD - Trump Tariff Alert` manualmente.
3. Rodar `PROD - Market Reaction Engine` manualmente.
4. Rodar `PROD - Brazil Local Alert` manualmente.
5. Rodar `PROD - BCB Direct Macro` manualmente.
6. Abrir o dashboard e confirmar historico e saude das fontes.

## 5. Como interpretar o resultado

- Execucao verde e sem Telegram: o filtro bloqueou corretamente.
- Node vermelho no Telegram: problema de credencial ou `chat_id`.
- Node vermelho no RSS/HTTP: problema de fonte ou URL.
- Dashboard vazio: o alerta nao passou pelo `Record ... Alert`.

## 6. Brasil Local

Regra atual:

- `YELLOW`: monitoramento
- `ORANGE`: viés ja util para intraday
- `RED`: impacto forte, acao mais agressiva

O usuario final deve ver:

- `Tendencia`
- `Conviccao`
- `Leitura WIN`
- `Leitura Dolar`
- `Confirmar`
- `Invalidar`

Nao deve depender de score para operar.

## 7. O que ainda falta

- Dashboard completo com dados em tempo real do `Profit`
- Camada de login, assinatura e pagamento com `Stripe`
- Melhor consolidacao de feed real por camada
- Persistencia historica mais rica para analise de qualidade
- Refinar a calibracao do BCB direto depois do primeiro uso real em dia util

## 8. Regra de producao

Nao ative workflow com feed real antes de validar:

- URL RSS funcionando
- dashboard respondendo
- Telegram e Discord entregando
- dedupe registrando corretamente
