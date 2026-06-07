# Super Manual Operacional Noob

Este manual e para quem nunca usou o projeto antes.

## O que este projeto faz

Ele observa noticias e dados de mercado, decide se existe alerta relevante, grava o resultado localmente e envia a leitura para Telegram e Discord.

## O que voce precisa saber antes de tudo

- `n8n` e o motor dos fluxos.
- O dashboard local mostra historico e saude das fontes.
- O banco local guarda os alertas para nao repetir a mesma noticia.
- Telegram e Discord sao os canais de saida.

## O que ja esta pronto

- Envio de teste para Telegram.
- Envio de teste para Discord.
- Fluxo de noticias de tarifa.
- Fluxo de reacao de mercado.
- Fluxo Brasil Local.
- Dashboard local.
- Banco local.
- Dedupe para nao spammar a mesma noticia.
- Lista de fontes com pesos e thresholds.

## O que ainda falta neste momento

- URLs RSS.app reais de todas as fontes Brasil Local que ainda estao vazias.
- Dashboard final mais bonito e mais completo.
- Integracao com dados em tempo real do `Profit`.
- Login, assinatura e pagamento com `Stripe`.

## Como saber se esta tudo funcionando

Voce vai ver 4 sinais:

1. O workflow executa sem erro.
2. O Telegram ou Discord recebem a mensagem.
3. O dashboard registra o alerta.
4. A mesma noticia nao fica repetindo sem motivo.

Se os 4 acontecerem, o sistema esta vivo.

## O que abrir primeiro

1. Abra o `n8n`.
2. Abra o dashboard local.
3. Abra o Telegram.
4. Abra o Discord.

## Como iniciar o sistema local

No PowerShell, dentro da pasta do projeto:

```powershell
.\scripts\start-alert-dedupe-service.ps1
```

Se o servico subir, abra:

```text
http://127.0.0.1:8787/dashboard
```

## Como testar sem risco

### Teste 1: Telegram de fumaça

Use o workflow:

```text
TEST - Telegram Smoke Test
```

O que esperar:
- chega 1 mensagem de teste
- se chegar mais de uma, o teste foi repetido
- se nao chegar nada, o bot ou o `chat_id` estao errados

### Teste 2: Discord de fumaça

Use o fluxo de teste do Discord.

O que esperar:
- chega 1 mensagem de teste no canal
- se nao chegar, o webhook do Discord esta errado

### Teste 3: Noticias fortes

Use:

```text
PROD - Trump Tariff Alert
```

O que esperar:
- se a noticia for forte, envia
- se a noticia for fraca, nao envia
- se repetir a mesma manchete, o dedupe deve bloquear

### Teste 4: Mercado

Use:

```text
PROD - Market Reaction Engine
```

O que esperar:
- o fluxo pega leitura de mercado
- monta o regime
- envia somente quando ha mudanca material

### Teste 5: Brasil Local

Use:

```text
PROD - Brazil Local Alert
```

O que esperar:
- ele le BCB, IBGE, UOL e fontes locais
- mostra se o viés do WIN e de alta ou baixa
- nao precisa mostrar score para o usuario final

## Como interpretar as cores

- `GREEN`: sem sinal importante.
- `YELLOW`: ruido util, monitorar.
- `ORANGE`: alerta importante, mas ainda nao extremo.
- `RED`: impacto alto, exige atencao.

## Como o usuario final deve ver a mensagem

Nao deve ver um monte de score.
Deve ver isto:

- `Titulo`
- `Tendencia`
- `Conviccao`
- `Leitura WIN`
- `Leitura Dolar`
- `Leitura Nasdaq/ES`
- `Motivo`
- `Fonte`

## Como evitar spam

O sistema usa 3 coisas:

1. Threshold.
2. Dedupe.
3. Cooldown.

Se a mesma noticia sair de novo em pouco tempo, ela nao deve voltar.
Se o mercado piorar de verdade, ele pode reenviar como update.

## O que voce deve fazer no dia a dia

1. Abrir o dashboard.
2. Ver se as fontes estao verdes.
3. Rodar um teste de Telegram ou Discord.
4. Rodar um workflow real manualmente.
5. Conferir se o alerta chegou.
6. Se funcionar, deixar em live.

## O que esta faltando para a fase atual ser realmente fechada

1. Colocar as URLs RSS.app reais do Brasil Local que ainda faltam.
2. Validar essas URLs em dia util.
3. Confirmar os thresholds com historico real.
4. Ligar Brasil Local no n8n sem spam.
5. Melhorar o dashboard final.

## Regra simples

Se voce se perder:

1. Abra o dashboard.
2. Rode o teste de Telegram.
3. Rode um workflow real.
4. Veja qual node ficou vermelho.
5. Leia este manual de novo.
