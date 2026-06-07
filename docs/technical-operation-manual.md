# Manual Tecnico de Operacao v1

Este manual explica como subir, testar e entender o projeto sem depender da conversa.

## 1. O que existe hoje

- `TEST - Telegram Smoke Test`
- `PROD - Trump Tariff Alert`
- `PROD - Market Reaction Engine`
- `PROD - Brazil Local Alert`
- `PROD - BCB Direct Macro`

## 2. O que cada fluxo faz

| Fluxo | Funcao |
| --- | --- |
| `TEST - Telegram Smoke Test` | Envia 1 mensagem falsa para provar que Telegram funciona |
| `PROD - Trump Tariff Alert` | Lê noticias e dispara quando a manchete tem impacto forte |
| `PROD - Market Reaction Engine` | Lê ES, NQ, Gold e DXY para definir risco-on / risco-off |
| `PROD - Brazil Local Alert` | Lê fontes locais e gera vies para WIN, dolar e Brasil |
| `PROD - BCB Direct Macro` | Lê PTAX e expectativas oficiais do BCB por API direta |

## 3. Como subir o ambiente local

No PowerShell, dentro da raiz do projeto:

```powershell
.\scripts\start-alert-dedupe-service.ps1
.\scripts\start-n8n.ps1
```

O dashboard local fica em:

```text
http://127.0.0.1:8787/dashboard
```

## 4. Como importar os workflows

Se precisar reimportar tudo:

```powershell
.\scripts\import-workflow.ps1
```

Esse script importa:

- smoke test do Telegram
- tariff alert
- market reaction
- brazil local
- BCB direct macro

## 5. Como testar sem se perder

Ordem recomendada:

1. Rodar `TEST - Telegram Smoke Test`.
2. Rodar `PROD - Market Reaction Engine` manualmente.
3. Rodar `PROD - BCB Direct Macro` manualmente.
4. Rodar `PROD - Brazil Local Alert` manualmente.
5. Rodar `PROD - Trump Tariff Alert` manualmente.
6. Abrir o dashboard e confirmar historico e saude das fontes.

## 6. Como interpretar o resultado

- Workflow verde e sem alerta: o filtro bloqueou corretamente.
- Node vermelho no Telegram: problema de credencial, chat_id ou bot.
- Node vermelho no Discord: problema no webhook.
- Node vermelho no RSS/HTTP: problema de fonte, URL ou parser.
- Dashboard vazio: o alerta nao chegou no node de gravacao.

## 7. O que o usuario final deve enxergar

### Brasil Local

- `Tendencia`
- `Conviccao`
- `Leitura WIN`
- `Leitura Dolar`
- `Confirmar`
- `Invalidar`

### BCB Direct Macro

- `Tendencia`
- `Conviccao`
- `Leitura WIN`
- `Leitura Dolar`
- `Leitura Nasdaq/ES`
- `Leituras oficiais`

### Market Reaction

- `Regime`
- `Intensidade`
- `Tendencia`
- `Conviccao`
- `Plano WIN`
- `Plano Dolar`
- `Plano Nasdaq/ES`

## 8. Regras atuais

- `YELLOW`: monitoramento
- `ORANGE`: sinal util, mas ainda com cautela
- `RED`: impacto forte
- `RISK_OFF`: ES/NQ fracos com DXY/Gold confirmando
- `RISK_ON`: ES/NQ fortes com DXY cedendo

## 9. Onde cada coisa grava

| Workflow | Node | Endpoint |
| --- | --- | --- |
| `PROD - Trump Tariff Alert` | `Record News Alert` | `POST /api/alerts` |
| `PROD - Market Reaction Engine` | `Record Market Alert` | `POST /api/alerts` |
| `PROD - Brazil Local Alert` | `Record Brazil Local Alert` | `POST /api/alerts` |
| `PROD - BCB Direct Macro` | `Record BCB Direct Alert` | `POST /api/alerts` |

## 10. O que ainda falta

- Dashboard completo com dados em tempo real do `Profit`
- Camada de login, assinatura e pagamento com `Stripe`
- Melhor consolidacao de feed real por camada
- Persistencia historica mais rica para analise de qualidade
- Calibracao fina do BCB direto depois do uso em dia util

## 11. Regra de producao

Nao ative feed real antes de validar:

- URL funcionando
- dashboard respondendo
- Telegram entregando
- Discord entregando
- dedupe registrando corretamente

## 12. Observacao importante

O `Build Discord Test` do `PROD - Market Reaction Engine` usa `ES: mock`, `NQ: mock`, `Gold: mock` e `DXY: mock` apenas para teste manual. Isso nao faz parte do fluxo de producao.

