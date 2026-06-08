# Project Status

## Estado atual

O projeto ja saiu da fase de ideia e entrou na fase de operacao controlada.

### Ja existe

- Ingestao por RSS / feed para noticias editoriais
- Integracao direta com BCB para `PTAX` e `Expectativas`
- Scoring e filtros para noticias, mercado e macro local
- Telegram como canal ativo
- Discord ligado no `Trump Tariff Alert` e pronto para os outros fluxos
- Dashboard local com historico, preview lateral, links clicaveis e health tecnico
- Banco local SQLite para alertas, dedupe e health
- Camada Brasil Local separada da camada global
- Macro Monitor na Home com:
  - interno: `PTAX USD`, `Selic 2026`, `IPCA 2026`, `Cambio 2026`
  - externo: `ES`, `NQ`, `Gold`, `DXY`
- Atualizacao parcial do dashboard sem recarregar a pagina inteira
  - externo: rapido
  - interno: mais lento

### Em validacao

- URLs RSS.app reais restantes da camada Brasil Local
- thresholds de `Laranja` e `Vermelho` em dia util
- equilibrio entre ruido e sinal com mercado aberto
- rotina de dedupe e atualizacao de regime no fluxo de noticias
- leitura comparativa do `UOL` como apoio editorial
- expansao do BCB direto para mais endpoints se realmente agregar valor

### Falta construir

- Dashboard completo com dados em tempo real do `Profit`
- Onboarding de usuario final com conversao
- Pagamento com `Stripe`
- Historico analitico com filtros mais ricos
- Persistencia por usuario e plano
- Integracoes self-service por usuario para Telegram e Discord

## Prioridade real

1. Validar em dia util os fluxos com mercado e noticias reais
2. Fechar as URLs RSS.app que ainda faltarem para `UOL`, `Fazenda`, `Petrobras` e `Vale`
3. Ajustar thresholds e cooldown com base no historico de segunda-feira em diante
4. Ligar Discord nos outros workflows que ainda estao com placeholder
5. Consolidar onboarding e integracoes do usuario final
6. Depois integrar `Profit` e pagamentos

## Risco tecnico atual

O maior risco hoje nao e arquitetura. E calibracao operacional.

Se os feeds vierem ruins, o sistema vai continuar funcional, mas com menos valor.
Se os thresholds vierem baixos, vira spam.
Se vierem altos demais, vira um produto que quase nunca alerta.

## Nota de produto

O sistema deve ser vendido como leitura de vies e alerta operacional, nao como previsao garantida.

## O que falta para considerar esta fase fechada

- Placeholders reais de Discord preenchidos nos workflows restantes
- Teste real em dia util sem spam relevante
- Validacao final das fontes editoriais Brasil Local
- Pequena calibracao final de thresholds com mercado aberto

## V1 operacional

O manual tecnico de operacao `v1` desta fase foi fechado.

O que isso significa:

- existe uma ordem clara de teste
- os canais principais estao documentados
- o BCB direto ficou separado do RSS
- o teste manual do Market Reaction ficou explicitado como teste e nao producao
- o dashboard tem historico, preview e auditoria minima para operacao diaria
- a Home mostra o vies macro interno e externo sem depender de abrir outras telas
