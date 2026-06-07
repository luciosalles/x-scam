# Alert Calibration

Fonte de verdade operacional:
- [Alert Map](C:/Users/scorpion/Documents/X-Scam/docs/alert-map.md)

## Default profile

Comece com `balanced`.

So use `aggressive` em canal interno. Para clientes pagantes, migre para `conservative` quando tiver dados suficientes.

## Matriz de decisao

| Caso | Nivel sugerido | Racional |
| --- | --- | --- |
| White House/USTR/Federal Register + tariff + China/Mexico/EU | RED | Fonte oficial e canal direto de impacto |
| Fonte oficial + tarifa setorial sem pais claro | ORANGE | Pode afetar setor, mas precisa contexto |
| Reuters/AP confirma rumor de tarifa | ORANGE | Boa confianca, mas sem documento oficial |
| CNN/CNBC cita fontes anonimas | YELLOW/ORANGE | Depende de especificidade e velocidade |
| ZeroHedge/Investing sem confirmacao | YELLOW | Sinal de narrativa, nao de verdade |
| Delay/exemption/rollback de tarifa | ORANGE | Pode gerar risk-on/short-covering |
| Retaliacao China + rare earths/chips/autos | RED | Alta chance de choque em supply chain |

## Matriz Brasil Local

| Caso | Nivel sugerido | Racional |
| --- | --- | --- |
| Copom hawkish + DI abrindo + dolar firme | RED | Juros e cambio pressionam WIN de forma direta |
| IPCA acima do esperado + mercado repricing Selic | RED | Inflacao acelera precificacao de juros |
| Tesouro / fiscal piorando + Fazenda ruindo narrativa | RED | Juros longos e dolar tendem a reagir |
| Petrobras ou Vale muito fracas + dolar forte | ORANGE/RED | Peso indexador relevante no indice |
| Comunicados do BC sem surpresa forte | YELLOW | Serve para contexto, nao para acao direta |
| Falas da Fazenda ambíguas sem dado novo | YELLOW/ORANGE | Ruido importante, mas precisa confirmacao |
| Reversao local com DI cedendo e dolar perdendo forca | ORANGE | Melhor para short cover ou alivio do WIN |

## Campos para log

Use Google Sheets, Airtable ou Postgres com estes campos:

```text
timestamp
source_id
source_layer
headline
url
pre_score
ai_score
alert_level
sent_to_public
nas100_5m
nas100_15m
nas100_60m
spx_15m
dxy_15m
gold_15m
was_useful
notes
```

## Ajustes depois de 48 horas

- Muitos falsos positivos: aumente `balanced.minScore` de 65 para 70.
- Poucos alertas bons: reduza `balanced.minScore` para 60, mas mantenha cooldown.
- Muito rumor virando alerta: reduza pesos de `news_validation` e `market_reaction`.
- Alerta oficial chegando tarde: priorize RSS.app update frequency para White House, USTR e Federal Register.
- Duplicatas: aumente `cooldownMinutesByFingerprint` para 45-60.

## Produto pago

Mensagem publica deve ser curta:

```text
RED | Tariff Alert
Fonte: White House
Viés: risk-off
NAS100: baixa forte
Confianca: 82%
Motivo: official tariff action + China/supply-chain channel.
```

Mensagem interna pode ser maior e incluir reasoning, link, score e entidades.

## Brasil Local

Para o dashboard final, a leitura deve aparecer assim:

```text
VIÉS DE BAIXA
WIN tende a cair se DI e dólar seguirem firmes.
Convicção: alta
O que confirma: Copom hawkish, IPCA acima do esperado, Petrobras/Vale fracas
O que invalida: DI cede, dólar perde força, WIN recupera VWAP
```
