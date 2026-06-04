# Make.com Scenario

Use Make.com se quiser velocidade de setup sem hospedar n8n.

## Modulos

1. RSS > Watch RSS feed items
2. Tools > Text aggregator ou Iterator
3. OpenAI/Anthropic/Grok via HTTP
4. Router por nivel de alerta
5. Telegram Bot > Send message
6. WhatsApp Cloud API ou Twilio > Send message
7. Google Sheets > Add row

## Cenario minimo

Crie um modulo RSS por camada critica:

- White House Presidential Actions
- White House Briefing Room
- USTR Press Office via RSS.app
- Federal Register tariff search via RSS.app/API
- Reuters Markets via RSS.app
- CNBC Markets via RSS.app

Depois envie cada item para IA com o prompt em `prompts/impact_classifier.md`.

## Filtros no Router

Filtro `RED`:

```text
impact_score >= 78 AND confidence >= 0.72
```

Filtro `ORANGE`:

```text
impact_score >= 60 AND confidence >= 0.62
```

Filtro interno `YELLOW`:

```text
impact_score >= 40
```

## HTTP para Claude/Grok/OpenAI

Use um modulo HTTP com:

```text
Method: POST
Headers:
  Authorization: Bearer YOUR_API_KEY
  Content-Type: application/json
Body:
  model
  messages / prompt
  temperature: 0.1
```

Temperatura baixa e output JSON obrigatorio. O alerta precisa ser consistente, nao criativo.

