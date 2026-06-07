# Discord Distribution

## Objetivo

Levar o `PROD - Market Reaction Engine` para um canal do Discord com o menor atrito possivel.

## Caminho recomendado

Use `Discord Webhook`.

Isso evita:
- criar bot completo
- lidar com OAuth
- gerenciar intents e permissoes mais complexas

## Como criar

1. No Discord, abra o canal desejado.
2. `Edit Channel`
3. `Integrations`
4. `Webhooks`
5. `New Webhook`
6. Copie a URL

## Como aplicar no n8n

Adicione um node `HTTP Request` depois do node `IF Market Alert Worthy`.

Configuracao:

- `Method`: `POST`
- `URL`: sua URL do webhook do Discord
- `Send Body`: `true`
- `Content Type`: `JSON`

Body:

```json
{
  "content": "={{$json.discordText}}"
}
```

## Estrategia de distribuicao

Telegram:
- melhor para alerta rapido e privado
- melhor para MVP e grupos pequenos

Discord:
- melhor para comunidade
- melhor para historico em canais
- melhor para separar por topicos

## Estrutura recomendada de canais

- `#market-reaction-live`
- `#tariff-alerts`
- `#macro-context`
- `#setup-and-status`

## Estrategia operacional

Use o mesmo score engine e distribua para dois destinos:

1. Telegram
2. Discord

Nao crie uma logica diferente para cada canal.

O ideal e:
- um motor de decisao
- multiplos canais de saida

## Proximo passo

Quando voce tiver a URL do webhook:

1. adicionar node `Discord Webhook`
2. enviar `{{$json.discordText}}`
3. testar manualmente
4. ativar em producao
