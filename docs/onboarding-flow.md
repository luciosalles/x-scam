# Onboarding Flow

Fluxo final de onboarding para conversao, limitado a 6 telas.

## Tela 1 - Boas-vindas

Objetivo:
- explicar em 1 frase o que o produto faz
- mostrar o ganho: alerta rapido, sem ruido, focado em WIN / dolar / macro

CTA:
- `Start free`
- `View live sample`

## Tela 2 - Escolha do modo

Opcoes:
- `Trader individual`
- `Grupo/mesa`
- `Leitura macro`

Efeito:
- ajusta densidade do alerta, thresholds e canais padrao

## Tela 3 - Conectar canal

Opcoes:
- `Telegram`
- `Discord`

UX recomendada:
- Telegram: botao `Open Telegram Bot` e o usuario aperta `Start`
- Discord: botao `Connect Discord` ou `Paste webhook`

Objetivo:
- esconder `chat_id`, token e webhook do usuario final

## Tela 4 - Selecionar foco

Checkboxes:
- `Brasil Local`
- `Externo / Global`
- `Mercado / Confirmacao`
- `Petrobras / Vale`
- `Somente high impact`

Objetivo:
- o usuario entende o que quer receber sem mexer em regra tecnica

## Tela 5 - Regras rapidas

Opcoes simples:
- `Mais agressivo`
- `Equilibrado`
- `Mais conservador`

Extras:
- `Avisar reversao`
- `Avisar apenas update material`
- `Cooldown por regime`

Objetivo:
- deixar o produto ajustavel sem abrir n8n

## Tela 6 - Teste e ativacao

Mostra:
- preview do alerta
- status da fonte
- teste de Telegram/Discord
- leitura em portugues com `Tendencia`, `Conviccao`, `Leitura WIN` e `Leitura Dolar`
- ativar notificacoes

CTA:
- `Send test alert`
- `Go live`

## Estrutura futura para MetaTrader

Depois, uma etapa opcional:
- conectar um feed de candles WIN
- usar como camada de confirmacao ou invalidação
- nao substituir o feed de noticias
- manter como motor separado, alimentando o mesmo dashboard

## Sequencia ideal de conversao

1. Usuario entra e entende a promessa.
2. Conecta Telegram em menos de 30 segundos.
3. Escolhe Brasil Local, Global ou ambos.
4. Recebe um teste.
5. Vê fonte viva e historico.
6. Ativa e volta depois para ajustar.
