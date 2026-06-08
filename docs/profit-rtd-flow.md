# Profit RTD Flow

Este modulo separa o `Profit RTD` do restante do sistema.

## Objetivo

Transformar o `RTD` do Profit em:

- scanner de campos validos
- stream de ticks em tempo quase real
- buffer rolling em memoria
- historico em `Parquet`
- leitura visual no menu `RTD Flow` do dashboard

## Arquivos principais

- [profit_rtd_config.json](C:/Users/scorpion/Documents/X-Scam/config/profit_rtd_config.json)
- [profit_rtd_flow.py](C:/Users/scorpion/Documents/X-Scam/scripts/profit_rtd_flow.py)
- [profit_rtd_stream.ps1](C:/Users/scorpion/Documents/X-Scam/scripts/profit_rtd_stream.ps1)
- [start-profit-rtd-flow.ps1](C:/Users/scorpion/Documents/X-Scam/scripts/start-profit-rtd-flow.ps1)
- [rtd_callback_probe.ps1](C:/Users/scorpion/Documents/X-Scam/scripts/rtd_callback_probe.ps1)

## Comandos

Scanner antigo:

```powershell
python scripts\profit_rtd_flow.py scan
```

Status:

```powershell
python scripts\profit_rtd_flow.py status
```

Stream continuo:

```powershell
.\scripts\start-profit-rtd-flow.ps1
```

Plot manual:

```powershell
python scripts\profit_rtd_flow.py plot
```

Smoke test do callback RTD:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\rtd_callback_probe.ps1
```

Esse probe usa um `IRTDUpdateEvent` COM/.NET real para validar o ciclo:

- `ServerStart(callback)`
- `ConnectData(...)`
- `RefreshData(...)`

Se ele passar, o servidor do Profit aceita o callback; se falhar, o bloqueio é de contrato COM e nao de simbolo.

## Saidas geradas

Pasta:

```text
data/rtd/
```

Arquivos:

- `state.json`: estado atual do coletor
- `snapshot.json`: simbolos e ticks recentes
- `discovery.json`: resultado do scanner
- `latest_ticks.parquet`: rolling buffer mais recente
- `flow_overview.png`: plot tecnico
- `chunks/*.parquet`: blocos historicos

## Erro comum

Se aparecer:

```text
Invalid class string
```

o `PROFIT.RTD` nao esta registrado no Windows atual.

Isso nao quebra o dashboard. O menu `RTD Flow` vai mostrar o erro e continuar vivo.

## Smoke test validado

O probe `scripts/rtd_callback_probe.ps1` ja conseguiu:

- `ServerStart=1`
- `ConnectData` retornando valor
- `RefreshData` retornando dados

Esse é o host RTD validado para o projeto.

O stream continuo `scripts/profit_rtd_stream.ps1` usa o mesmo contrato e escreve:

- `state.json`
- `snapshot.json`
- `discovery.json`

na pasta `data/rtd/` para o dashboard ler em tempo real.

## Integracao com dashboard

O dashboard le:

- `GET /api/rtd/overview`
- `GET /rtd/plot`

Entao a pagina `RTD Flow` depende do coletor ter escrito arquivos em `data/rtd/`.
