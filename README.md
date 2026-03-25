# Alerta de Editais de Residência Médica

Sistema automatizado de notificação de novos editais de residência médica do portal **Estratégia MED** diretamente para o seu chat no **Microsoft Teams**.

## Tecnologias

- **Python 3.11** com `requests` e `lxml` para coleta dos dados (Scraping)
- **Google Gemini 1.5 Flash** para NLP e filtro dos editais reais.
- **Power Automate Workflows** para webhook do Teams (Notificação via Adaptive Card).
- **GitHub Actions** para orquestração (Cron Scheduler).

## Configuração

1. Fork ou clone este repositório.
2. Na aba **Settings > Secrets and variables > Actions** do GitHub, crie os seguintes segredos de repositório (Repository secrets):
   - `GEMINI_API_KEY`: Sua chave de API do Google AI Studio.
   - `TEAMS_WEBHOOK_URL`: O link do webhook do Workflow criado no Teams, que recebe mensagens no chat.

## Estrutura Automática

- O cron executa o fluxo automaticamente a cada 1 HORA.
- O resultado das rodadas é guardado no arquivo `data/last_seen.json`.
- Mensagens e notificações repetidas não ocorrerão pois ele armazena qual foi o último visualizado baseado nos links únicos da plataforma.
