# Brazil Local RSS.app Runbook

Este e o roteiro operacional da proxima etapa. A parte que depende da sua conta do RSS.app e gerar as URLs reais; o resto ja fica versionado no projeto.

## 20 etapas

1. Abrir `config/brazil_local_rss_app_seed_list.csv`.
2. Comecar pelas fontes de prioridade `1`.
3. Abrir o RSS.app Feed Generator.
4. Colar a primeira `page_url` oficial.
5. Gerar o feed automatico.
6. Se a pagina falhar, usar RSS Builder.
7. Salvar o feed em `My Feeds` no RSS.app.
8. Copiar a URL RSS gerada.
9. Abrir `config/brazil_local_rss_app_urls.json`.
10. Colar a URL no campo `rss_url` da fonte correta.
11. Trocar `enabled` para `true` somente nessa fonte.
12. Rodar `.\scripts\validate-brazil-local-rss.ps1`.
13. Se der `ok`, repetir para a proxima fonte.
14. Se der `bad_content`, recriar no RSS Builder.
15. Se der `error`, testar a URL no browser e revisar permissao/plano do RSS.app.
16. Reimportar workflows com `.\scripts\import-workflow.ps1`.
17. No n8n, rodar `PROD - Brazil Local Alert` manualmente.
18. Confirmar que nodes ficam verdes.
19. Confirmar no dashboard se algum alerta foi gravado.
20. Ativar o workflow so depois de testar em dia util com mercado aberto.

## Regra de calibracao

No sabado ou domingo, use apenas smoke test e health check. A calibracao real de `Laranja` e `Vermelho` deve ser feita em dia util, olhando a reacao de `WIN`, dolar, DI, Petrobras e Vale.

## O que significa sucesso

- `validate-brazil-local-rss.ps1` mostra `ok` nas fontes habilitadas.
- O workflow roda sem erro mesmo quando nao ha alerta.
- O dashboard abre em `http://127.0.0.1:8787/dashboard`.
- Telegram e Discord so recebem alerta quando o filtro deixa passar.
