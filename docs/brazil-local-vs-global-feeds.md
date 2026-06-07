# Brazil Local vs Global Feeds

Objetivo: separar o que mexe com `WIN` por fator domestico do que vem de fora.

## Regra base

| Bloco | Pergunta que responde | Peso no WIN |
| --- | --- | --- |
| Brasil Local | O que altera juros, fiscal, Petrobras, Vale e o humor interno? | Alto |
| Externo / Global | O que muda risco global, dolar e apetite a risco? | Medio-alto |
| Mercado / Confirmacao | O que confirma o movimento em tempo real? | Alto para entrada, baixo para narrativa |

## Brasil Local

### 1. Politica monetaria

Fontes:
| Fonte | Uso |
| --- | --- |
| Banco Central do Brasil | Copom, comunicados, ata, discursos |
| Agenda BCB | calendario de eventos oficiais |
| Reuters Brasil economia | agregador rapido para falas e repercussao |

Sinais que importam:
- Selic, ata e comunicado do Copom
- tom hawkish/dovish
- sinais sobre corte, pausa ou alta

### 2. Inflacao

Fontes:
| Fonte | Uso |
| --- | --- |
| IBGE / IPCA | inflacao oficial |
| IBGE / IPCA-15 | leitura adiantada |
| Focus / BCB | expectativa de mercado |

Sinais que importam:
- surpresa de IPCA
- servicos e difusao
- desancoragem de expectativas

### 3. Fiscal e Fazenda

Fontes:
| Fonte | Uso |
| --- | --- |
| Ministerio da Fazenda | comunicados, entrevistas, medidas |
| Tesouro Nacional | resultado fiscal, divida, operacoes |
| Receita Federal | medidas de arrecadacao, regras e comunicados |

Sinais que importam:
- piora fiscal
- contingenciamento
- mudanca de narrativa da Fazenda
- ruído politico com efeito em juros longos

### 4. Mercado local

Fontes:
| Ativo | O que olhar |
| --- | --- |
| `WIN` | direcao do indice futuro brasileiro |
| `DOL` ou mini dolar | pressao cambial e fluxo defensivo |
| `DI1` | juros futuros, sensibilidade a fiscal e Copom |
| `PETR4` | peso indexador e sensibilidade a petroleo/fiscal |
| `VALE3` | peso indexador e ligacao com China/minerio |
| `minerio de ferro` | impacto em Vale e em humor de commodities |
| `petróleo` | Petrobras e risco geopolitico |

## Externo / Global

### 1. EUA macro

Fontes:
| Fonte | Uso |
| --- | --- |
| BLS | Payroll, CPI, emprego |
| Federal Reserve | discurso, FOMC, liquidez |
| Treasury | curvas e emissao |

### 2. Comercio e tarifa

Fontes:
| Fonte | Uso |
| --- | --- |
| White House | anuncios presidenciais |
| USTR | Section 301, trade actions |
| Federal Register | publicacao formal |

### 3. Noticia rapida

Fontes:
| Fonte | Uso |
| --- | --- |
| Reuters | primeiro resumo confiavel |
| AP | confirmacao wire |
| CNN / CNBC / MarketWatch | narrativa para contexto |

## Separacao recomendada no n8n

| Workflow | Entrada | Saida |
| --- | --- | --- |
| `PROD - Brazil Local Alert` | BCB, IBGE, Fazenda, Tesouro, B3, Petrobras, Vale, minerio, petroleo | Telegram, dashboard |
| `PROD - Global Macro Alert` | White House, USTR, BLS, Fed, Reuters, AP | Telegram, dashboard |
| `PROD - Market Reaction Engine` | ES, NQ, DXY, Gold, DOL, DI, WIN | Telegram, Discord, dashboard |

## Prioridade de montagem

1. Primeiro: Brasil Local.
2. Segundo: Externo / Global.
3. Terceiro: Confirmacao de mercado.
4. Quarto: dashboard e historico por fonte.

## Ideia de scoring

| Camada | Score base |
| --- | --- |
| Oficial Brasil | 100 |
| Fiscal / Fazenda | 90 |
| Mercado local | 85 |
| Reuters / AP | 75 |
| Mid-tier news | 60 |
| Social / rumor | 30 |

## Proxima fase pratica

Quando for implementar:
- criar feeds separados por camada
- marcar `region: BR` ou `region: GLOBAL`
- marcar `theme: monetary`, `fiscal`, `market`, `trade`
- aplicar thresholds diferentes por bloco
- montar um score final para `WIN` a partir da combinacao

## Lista concreta de feeds Brasil Local

Arquivo de referencia:

`config/brazil_local_feed_layers.json`

### Camada 1 - Politica monetaria

| Feed | URL base | Uso |
| --- | --- | --- |
| BCB - Comunicados do Copom | `https://www.bcb.gov.br/controleinflacao/comunicadoscopom/cronologicos` | Selic, decisão e tom do BC |
| BCB - Atas do Copom | `https://www.bcb.gov.br/publicacoes/atascopom/cronologicos` | leitura fina do tom e guia para DI |
| BCB - Calendario do BC | `https://www.bcb.gov.br/acessoinformacao/calendariobc` | agenda de eventos e publicacoes |
| BCB - Notas a imprensa | `https://www.bcb.gov.br/index.html` | notas urgentes e comunicados institucionais |

### Camada 2 - Inflacao e atividade

| Feed | URL base | Uso |
| --- | --- | --- |
| IBGE - Releases gerais | `https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa.html?lang=pt-BR` | IPCA, IPCA-15, PIB, industria, servicos |
| IBGE - Tag IPCA | `https://agenciadenoticias.ibge.gov.br/agencia-noticias.html?start=0&tag=IPCA` | foco em inflacao |
| IBGE - Busca IPCA | `https://agenciadenoticias.ibge.gov.br/busca-avancada.html?contem=ipca` | filtro adicional para releases de inflacao |

### Camada 3 - Fiscal e Fazenda

| Feed | URL base | Uso |
| --- | --- | --- |
| Tesouro Nacional - Noticias | `https://www.gov.br/tesouronacional/pt-br/noticias` | fiscal, emissao, divida, superavit, deficit |
| Tesouro Nacional - RTN | `https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/resultado-do-tesouro-nacional-rtn` | resultado fiscal mensal |
| Ministério da Fazenda - Noticias | `https://www.gov.br/fazenda/pt-br/assuntos/noticias` | falas, medidas e ruído fiscal/politico |

### Camada 4 - Mercado local e confirmacao

| Feed | URL base | Uso |
| --- | --- | --- |
| B3 - Futuro de Ibovespa | `https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/mercado-de-acoes/futuro-de-ibovespa.htm` | referencia oficial de WIN |
| B3 - Mercado Futuro | `https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/mercado-de-acoes/mercado-futuro.htm` | mapa dos futuros relevantes |
| B3 - DI1 | `https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/juros/futuro-de-taxa-media-de-depositos-interfinanceiros-de-um-dia.htm` | referencia de juros futuros |
| B3 - DIT / TAS de DI | `https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/juros/operacao-estruturada-de-trade-at-settlement-de-futuro-de-di-dit.htm` | microestrutura de DI |
| B3 - Mini Dolar | `https://edu.b3.com.br/w/mini-dolar` | referencia de dolar local |
| B3 - Dolar Comercial futuro | `https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/moedas/futuro-mini-de-taxa-de-cambio-de-reais-por-dolar-comercial.htm` | contexto de cambio |
| B3 - VIX Brasil | `https://www.b3.com.br/en_us/products-and-services/trading/equities/s-p-b3-bovespa-vix-index-future.htm` | volatilidade e stress de mercado |

### Camada 5 - Petrobras e Vale

| Feed | URL base | Uso |
| --- | --- | --- |
| Petrobras - Agencia de Noticias | `https://agencia.petrobras.com.br/pt` | dividendos, producao, precificacao, investimentos |
| Petrobras - IR | `https://petrobras.com.br/en` | resultados e comunicados ao mercado |
| Vale - Informacoes para o mercado | `https://www.vale.com/pt/informacoes-para-o-mercado` | comunicados, resultados e agenda |
| Vale - Press Releases | `https://vale.com/en/press-releases` | operacao, resultados e eventos corporativos |

## Como levar para o RSS.app

Use cada `URL base` como entrada no RSS.app.
Para o n8n, o node `RSS Feed Read` deve apontar para a URL RSS gerada pelo RSS.app, nao para a pagina original.

## Ordem de montagem

1. Comece com `BCB - Comunicados do Copom`.
2. Adicione `IBGE - Releases gerais` e `IBGE - Tag IPCA`.
3. Adicione `Tesouro Nacional - Noticias` e `RTN`.
4. Feche com `B3 - Futuro de Ibovespa`, `DI1`, `Mini Dolar`, Petrobras e Vale.
5. Depois separe os feeds em duas saidas: `Brasil Local` e `Externo`.
