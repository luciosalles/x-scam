# BCB Direct Integration

Use esta trilha para tirar o Banco Central do fluxo RSS e colocar o projeto em cima de fontes oficiais de dados.

## Arquitetura correta

- `RSS.app`: apenas fontes editoriais e humanas
- `API direta`: BCB PTAX, Expectativas de Mercado e series especificas
- `Mercado`: ES, NQ, DXY, Gold, dolar local, DI, Petrobras, Vale

Regra:

- noticia humana entra via RSS
- dado oficial entra via `HTTP Request`
- nunca force BCB a caber em RSS

## Endpoints oficiais para o n8n

### PTAX

Base oficial:

- `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/`
- `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/swagger-ui3#/`

Endpoint util para fechamento do USD:

```text
https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='06-01-2026'&@dataFinalCotacao='06-05-2026'&$format=json
```

Endpoint util para dia especifico:

```text
https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='06-05-2026'&$format=json
```

Campos principais:

- `cotacaoCompra`
- `cotacaoVenda`
- `dataHoraCotacao`
- `tipoBoletim`

### Expectativas de Mercado

Base oficial:

- `https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/`
- `https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/swagger-ui3#/`
- `https://dadosabertos.bcb.gov.br/dataset/expectativas-mercado`

Selic anual, ano corrente, base ampla:

```text
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?$filter=Indicador eq 'Selic' and DataReferencia eq '2026' and baseCalculo eq 0&$top=10&$orderby=Data desc&$format=json
```

IPCA anual, ano corrente, base ampla:

```text
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?$filter=Indicador eq 'IPCA' and DataReferencia eq '2026' and baseCalculo eq 0&$top=10&$orderby=Data desc&$format=json
```

Cambio anual, ano corrente, base ampla:

```text
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?$filter=Indicador eq 'C%C3%A2mbio' and DataReferencia eq '2026' and baseCalculo eq 0&$top=10&$orderby=Data desc&$format=json
```

Se quiser detalhe adicional de reunioes de Selic:

```text
https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoSelic?$filter=baseCalculo eq 0&$top=20&$orderby=Data desc&$format=json
```

Campos principais:

- `Data`
- `DataReferencia`
- `Mediana`
- `Media`
- `DesvioPadrao`
- `numeroRespondentes`
- `baseCalculo`

### SGS

Trate SGS como camada opcional, nao como motor principal.

Use apenas quando voce souber exatamente qual serie quer usar para o score.

Boas candidatas futuras:

- juros
- atividade
- credito
- liquidez

## Nodes no n8n

### Workflow recomendado

`PROD - BCB Direct Macro`

Nodes:

1. `Manual Trigger`
2. `Schedule Trigger`
3. `HTTP Request - Fetch PTAX Period`
4. `HTTP Request - Fetch Selic Expectations`
5. `HTTP Request - Fetch IPCA Expectations`
6. `HTTP Request - Fetch Cambio Expectations`
7. `Code - Score BCB Direct`
8. `If - Alert Worthy`
9. `Telegram`
10. `Discord`
11. `HTTP Request - Record Alert`

## Logica de score recomendada

### PTAX

- dolar fechando forte para cima aumenta vies de baixa para WIN
- dolar fechando para baixo alivia WIN

### Expectativas Selic

- mediana subindo piora juros Brasil
- mediana caindo alivia juros Brasil

### Expectativas IPCA

- IPCA subindo piora leitura de juros e bolsa
- IPCA caindo ajuda leitura de alivio

### Expectativas Cambio

- cambio esperado subindo reforca defesa e pressao em ativos locais
- cambio esperado caindo reduz estresse local

## Divisao profissional de workflows

- `PROD - Global Tariff / Macro News`: noticias globais
- `PROD - Market Reaction Engine`: ES, NQ, DXY, Gold
- `PROD - Brazil Local RSS`: UOL, Fazenda, Petrobras, Vale, Tesouro, IBGE
- `PROD - BCB Direct Macro`: PTAX e Expectativas oficiais
- `TEST - Telegram Smoke`
- `TEST - Discord Smoke`

## O que sai do RSS

O BCB deve sair de:

- `config/brazil_local_rss_app_urls.json`
- `config/brazil_local_rss_app_seed_list.csv`
- node `Brazil Local Feeds`

O BCB deve entrar em:

- `config/bcb_direct_endpoints.json`
- workflow `PROD - BCB Direct Macro`

## O que isso melhora

- menos fragilidade
- menos scraping desnecessario
- menos dependencia de HTML mudar
- mais confianca no dado
- mais cara de produto profissional
