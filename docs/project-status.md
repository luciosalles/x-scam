# Project Status

## Estado atual

O projeto ja saiu da fase de ideia e entrou na fase de integracao operacional.

### Ja existe

- Ingestao por RSS / feed
- Scoring e filtros para noticias e mercado
- Telegram como canal principal
- Discord preparado como segundo canal
- Dashboard local com historico e health check
- Banco local SQLite para alertas e fontes
- Camada Brasil Local separada

### Em validacao

- URLs RSS.app reais da camada Brasil Local
- threshold de `Laranja` e `Vermelho`
- equilibrio entre ruido e sinal
- rotina de dedupe e atualizacao de regime
- leitura comparativa do UOL como backup de mercado
- integracao oficial do BCB com `focus`, `cambio`, `normativos` e `atascomef`

### Falta construir

- Dashboard completo com dados em tempo real do `Profit`
- Onboarding de usuario final com conversao
- Pagamento com `Stripe`
- Historico analitico melhor para calibracao
- Persistencia por usuario e plano

## Prioridade real

1. Fechar RSS.app real do Brasil Local
2. Validar ruido e thresholds em dia util
3. Consolidar dashboard minimo com historico
4. Planejar login e monetizacao
5. Depois integrar `Profit` e pagamentos
6. Finalizar dashboard mais bonito e onboarding mais simples

## Risco tecnico atual

O maior risco hoje nao e arquitetura. E calibracao.

Se os feeds vierem ruins, o sistema vai continuar funcional, mas com menos valor.
Se os thresholds vierem baixos, vira spam.
Se vierem altos demais, vira um produto que quase nunca alerta.

## Nota de produto

O sistema deve ser vendido como leitura de vies e alerta operacional, nao como previsao garantida.

## O que falta para considerar esta fase fechada

- Todas as fontes Brasil Local importantes com URL valida
- Teste real em dia util sem spam
- Mensagens finais padronizadas
- Dashboard com historico util
- Manual operacional unico para usuario iniciante
