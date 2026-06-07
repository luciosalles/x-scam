# Market Reaction Engine

Este workflow monitora reacao de mercado a cada 30 segundos e deve rodar separado do fluxo de noticias.

Fonte de verdade operacional:
- [Alert Map](C:/Users/scorpion/Documents/X-Scam/docs/alert-map.md)

## Fonte atual

MVP usa Stooq CSV:

```text
https://stooq.com/q/l/?s=es.f+nq.f+gc.f+dx.f&f=sd2t2ohlcv&h&e=csv
```

Ativos:

- `ES.F`: S&P 500 E-mini futures
- `NQ.F`: Nasdaq 100 futures
- `GC.F`: Gold futures
- `DX.F`: Dollar Index futures

`US10Y` ainda nao entra como gatilho porque a fonte intraday gratuita precisa ser validada. Para producao, use uma API paga ou broker data feed.

## Regra de alerta

O workflow so envia Telegram quando existe confluencia forte:

- ES ou NQ caindo forte
- DXY ou Gold confirmando stress
- ou movimento risk-on forte com DXY cedendo

Tambem existe cooldown de 30 minutos para evitar spam.

## Como saber se funcionou

- `Fetch Market CSV` verde com 1 item: a fonte Stooq respondeu.
- `Score Market Snapshot` verde com 0 itens: o mercado foi lido, mas nao houve confluencia forte.
- `Telegram Market Alert` verde: alerta real enviado.
- `Node was not executed` depois do `IF`: normal quando o score ficou abaixo do limite.

Threshold atual:

```text
score >= 100
```

## Uso correto

Este fluxo nao substitui o fluxo de noticias. Ele confirma se o mercado esta reagindo.

Exemplo de produto:

```text
News Engine: detectou headline de tarifa.
Market Reaction Engine: ES/NQ caem e DXY/Gold sobem.
Resultado: alerta RED com mais confianca.
```

## Limitacao

Stooq pode ter atraso e nao deve ser vendido como dado institucional em tempo real. Para clientes pagos, considere Polygon, Twelve Data, MarketData.app, Tradier, Interactive Brokers, dxFeed, Rithmic, TradingView ou broker API.
