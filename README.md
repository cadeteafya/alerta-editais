# Alerta de Editais de Residência Médica

Sistema automatizado de notificação de novos editais de residência médica a partir do seu portal curado **Edital Tracker** diretamente para o seu chat no **Microsoft Teams** via Adaptive Cards de alta qualidade.

## Tecnologias

- **Python 3.11** com `requests` e `lxml` para coleta dos dados (Scraping estruturado)
- **Power Automate Workflows** para webhook do Teams (Notificação via Adaptive Card premium).
- **GitHub Actions** para orquestração (Cron Scheduler).

## Configuração

1. Fork ou clone este repositório.
2. Na aba **Settings > Secrets and variables > Actions** do GitHub, crie o seguinte segredo de repositório (Repository secret):
   - `TEAMS_WEBHOOK_URL`: O link do webhook do Workflow criado no Teams, que recebe mensagens no chat.
3. Certifique-se de dar permissões de escrita para os workflows em **Settings > Actions > General > Workflow permissions** selecionando **"Read and write permissions"** (necessário para persistir o histórico).

## Funcionamento Técnico

- O cron executa o fluxo automaticamente nos horários programados.
- O resultado das rodadas é guardado no arquivo `data/last_seen.json`.
- Mensagens e notificações repetidas ou duplicadas não ocorrerão. O sistema gera uma chave composta exclusiva `Título | Data de Publicação`, permitindo que novas atualizações ou retificações de um mesmo edital disparem novos alertas instantaneamente, enquanto editais inalterados permanecem silenciados.
