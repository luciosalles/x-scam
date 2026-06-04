# Setup RSS.app + n8n

## 1. Criar feeds no RSS.app

Comece pelas fontes da camada `official_primary` em `config/feed_layers.json`.

Prioridade do primeiro dia:

1. White House - Presidential Actions
2. White House - Briefing Room
3. USTR - Press Office
4. Federal Register - tariff search
5. Treasury - Press Releases
6. OFAC - Recent Actions
7. Reuters Markets
8. CNBC Markets

No RSS.app, para cada fonte:

1. Cole a URL principal.
2. Gere o feed.
3. Ative atualizacao rapida, se o plano permitir.
4. Copie a URL RSS gerada.
5. Substitua ou acrescente a URL no workflow n8n.

## 2. Google Alerts

Crie alertas com entrega por RSS quando disponivel, ou email se RSS nao aparecer.

Queries recomendadas:

```text
"Trump" "tariff" "China"
"Trump" "tariff" "Mexico"
"White House" "tariff"
"USTR" "Section 301"
"reciprocal tariffs"
"import duties" "China"
"tariff exemption"
"semiconductors" "tariff"
"autos" "tariff"
"steel aluminum tariffs"
```

## 3. n8n

Fluxo minimo:

1. Schedule Trigger a cada 1-5 minutos.
2. RSS Read para cada feed.
3. Merge.
4. Code node para normalizar titulo, fonte, data e link.
5. Code node para scoring inicial.
6. IA para classificacao final usando `prompts/impact_classifier.md`.
7. IF por `alert_level`.
8. Telegram para `ORANGE` e `RED`.
9. WhatsApp apenas para `RED`.
10. Google Sheets/Postgres para log e calibracao.

## 4. Sensibilidade

Use `balanced` no comeco.

- `conservative`: menos ruido, melhor para cliente pagante.
- `balanced`: bom para MVP e validacao.
- `aggressive`: bom para pesquisa, mas gera falsos positivos.

## 5. Calibracao

Durante 48 horas, registre:

- headline
- fonte
- score calculado
- score da IA
- alerta enviado
- movimento em NAS100/SPX/DXY/Gold nos 5, 15 e 60 minutos seguintes
- se o alerta teria sido util ou ruidoso

Depois ajuste:

- peso da fonte
- pesos de palavras
- threshold de `ORANGE` e `RED`
- cooldown de duplicados

