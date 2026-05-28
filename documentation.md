# Alerta de Editais — Documentação Técnica

## 1. Visão Geral

Sistema automatizado de custo zero que monitora a página curada do usuário [Edital Tracker](https://edital-tracker-woad.vercel.app/) em busca de novos editais de residência médica e envia notificações estruturadas e premium em tempo real para o Microsoft Teams via Adaptive Cards.

**Stack:**

| Componente       | Tecnologia                                      |
| ---------------- | ------------------------------------------------ |
| Orquestração     | GitHub Actions (cron schedule + workflow_dispatch) |
| Scraper          | Python 3.11 (`requests` + `lxml`)                |
| Notificação      | Microsoft Teams (Power Automate Webhook)         |
| Persistência     | `data/last_seen.json` (commitado no repositório) |

---

## 2. Arquitetura

```
┌──────────────┐      ┌────────────────┐      ┌─────────────┐
│ GitHub Action │─────▶│  scraper.py    │─────▶│ notifier.py │
│  (cron job)  │      │ Extrai editais │      │ Webhook POST│
└──────────────┘      └────────────────┘      └──────┬──────┘
                                                     │
                                                     ▼
                                             ┌──────────────┐
                                             │  Power       │
                                             │  Automate    │
                                             │  (Workflow)  │
                                             └──────┬───────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │ Microsoft    │
                                             │ Teams Chat   │
                                             │ (Adaptive    │
                                             │  Card)       │
                                             └──────────────┘
```

**Fluxo de execução:**

1. O GitHub Actions dispara `src/main.py` conforme o agendamento cron.
2. `main.py` carrega o estado anterior (`data/last_seen.json`) e chama `scraper.py`.
3. `scraper.py` faz uma requisição HTTP ao portal curado e extrai os editais estruturados via XPath.
4. Para cada edital novo ou atualizado (gerado uma chave única combinando `Título + Data de Publicação`), `main.py` dispara a notificação direta.
5. O `notifier.py` formata o Adaptive Card com cabeçalho de urgência dinâmico, destaque do próximo marco e o cronograma completo.
6. `main.py` salva o novo estado no `last_seen.json` (apenas se a notificação foi enviada com sucesso) e o GitHub Actions commita o arquivo atualizado de volta no repositório.

---

## 3. Estrutura de Arquivos

```
alerta-editais/
├── .github/
│   └── workflows/
│       └── monitor.yml          # Configuração do GitHub Actions
├── data/
│   └── last_seen.json           # Estado persistido (chaves exclusivas de editais vistos)
├── src/
│   ├── main.py                  # Orquestrador principal
│   ├── scraper.py               # Web scraper do portal Edital Tracker
│   └── notifier.py              # Envio de notificações para o Teams
├── requirements.txt             # Dependências Python
├── README.md                    # Instruções de configuração
└── documentation.md             # Este documento
```

---

## 4. Módulos

### 4.1 `src/scraper.py`

Responsável pela extração de dados da página Edital Tracker do Vercel.

**`fetch_articles()`**
- Faz GET na Homepage `https://edital-tracker-woad.vercel.app/` simulando navegador.
- Parseia o HTML com `lxml` e extrai todos os elementos `<article>`.
- De cada edital extrai:
  - Título (`title`)
  - Instituição (`institution`)
  - Ano (`year`)
  - Tag de Status (`tag`)
  - Data de Publicação (`published_at`)
  - Próximo Marco (`next_milestone`) contendo etapa, data e tempo restante.
  - Cronograma completo (`schedule`) mapeando etapa e data.
  - Link Oficial da Banca (`official_link`)
- Mapeia uma chave única em `link` combinando `Title + Publication Date` (ex: `f"{title} | {pub_date}"`) para controle preciso de atualizações e retificações.
- Retorna lista de dicionários ricos estruturados.

### 4.2 `src/notifier.py`

Envio de notificações para o Microsoft Teams.

- Monta um payload JSON contendo um Adaptive Card v1.4 dentro de `attachments`.
- O card é dinâmico e premium:
  - **Banner de Cabeçalho**: Dinâmico com ícone 🏥. Se a Tag for *"Saiu o edital"*, usa o estilo `Attention` (vermelho); caso contrário, usa `Accent` (azul).
  - **Destaque do Próximo Marco**: Caixa colorida de destaque com a próxima data de ação.
  - **Tabela de Cronograma (FactSet)**: Exibe a lista ordenada de marcos. Caso o cronograma ultrapasse **10 linhas**, limita em 9 linhas e insere a mensagem: `"⚠️ Cronograma muito longo. Conferir diretamente no site."`.
  - **Ações**: Botão primário para o link oficial da banca e secundário para o tracker.
- Envia via POST para a URL do Webhook armazenada no secret `TEAMS_WEBHOOK_URL`.

### 4.3 `src/main.py`

Orquestrador que conecta os módulos de forma otimizada e livre de custos de IA.

- Carrega o estado de `data/last_seen.json`.
- Itera sobre os editais retornados pelo scraper.
- Ignora editais já notificados utilizando a chave de deduplicação composta.
- Dispara notificações diretamente via `notifier.py`.
- Salva o estado atualizado ao final da execução.     "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [...],
        "actions": [...]
      }
    }
  ]
}
```

### 4.4 `src/main.py`

Orquestrador que conecta os módulos.

- Carrega o estado de `data/last_seen.json`.
- Itera sobre os artigos retornados pelo scraper.
- Ignora artigos já presentes no estado (deduplicação por URL).
- Aplica `time.sleep(15)` entre cada artigo para respeitar o rate limit do Gemini Free Tier (5 req/min).
- Salva o estado atualizado ao final da execução.

### 4.5 `.github/workflows/monitor.yml`

Configuração do GitHub Actions.

| Parâmetro        | Valor                                                      |
| ---------------- | ----------------------------------------------------------- |
| Seg a Sex        | A cada 30 minutos, das 08:00 às 18:00 BRT (11:00–21:00 UTC) |
| Sáb e Dom        | Uma única execução às 13:00 BRT (16:00 UTC)                 |
| Execução manual  | Habilitada via `workflow_dispatch`                           |
| Python           | 3.11 com cache de pip                                       |

Após a execução do monitor, o workflow commita automaticamente o `last_seen.json` atualizado usando a identidade `action@github.com`.

---

## 5. Secrets (GitHub)

| Secret             | Descrição                                                    |
| ------------------ | ------------------------------------------------------------ |
| `GEMINI_API_KEY`   | Chave da API do Google AI Studio para acesso ao Gemini       |
| `TEAMS_WEBHOOK_URL`| URL gerada pelo Workflow do Power Automate no Microsoft Teams |

Configurados em: **Settings → Secrets and variables → Actions → Repository secrets**.

---

## 6. Dependências

```
requests>=2.31.0       # HTTP client para scraping e envio de webhooks
lxml>=4.9.3            # Parser HTML para extração via XPath
google-genai>=0.3.0    # SDK moderno do Google Gemini (substituto do google-generativeai)
```

---

## 7. Diagnóstico e Resolução de Problemas Encontrados

### 7.1 Modelo Gemini não encontrado (HTTP 404)

**Erro:**
```
models/gemini-1.5-flash is not found for API version v1beta
```

**Causa:** O pacote `google-generativeai` (legado) estava descontinuado e os modelos referenciados não eram mais resolvidos pela API v1beta.

**Resolução:**
- Migração do pacote `google-generativeai` para `google-genai` (SDK moderno).
- Alteração do model ID para `gemini-2.5-flash`.

### 7.2 Rate Limit do Gemini Free Tier (HTTP 429)

**Erro:**
```
429 RESOURCE_EXHAUSTED — Quota exceeded for metric: generativelanguage... limit: 20, model: gemini-2.5-flash
```

**Causa:** O Free Tier do `gemini-2.5-flash` (a partir de Março/2026) permite apenas 20 requisições **diárias**, além do limite de 5 requisições por minuto. Na primeira execução, com múltiplas notícias acumuladas, as 20 chamadas eram instantaneamente gastas. Os modelos da família 2.0 (como `gemini-2.0-flash`) foram testados, porém foram desativados oficialmente pelo Google para migração compulsória.

**Resolução:**
- O modelo primário programado em `ai_filter.py` foi migrado para `gemini-2.5-flash-lite`, que garante a cota monstruosa de **1.000 requisições diárias** grátis, mais que o suficiente pro escopo do bot.

### 7.3 Scraper bloqueado ou recebendo páginas "capadas" (Geo-Blocking e Error 403)

**Erro A:** 403 Forbidden para artigos individuais.
**Erro B:** O robô varre a Homepage principal, mas as notícias de grande impacto (ex: Revalida INEP) não são lidas, apesar de o usuário vê-las perfeitamente na capa de seu navegador.

**Causa A:** Faltava `Referer` nos requests de artigo.
**Causa B:** O GitHub Actions roda em servidores nos Estados Unidos. Quando ele acessa a Homepage padrão `https://med.estrategia.com/portal/`, o sistema do site detecta o IP internacional e entrega uma versão "capada" do portal (fallback layout) faltando os super destaques nacionais.

**Resolução:**
- `Referer` adicionado a todos os acessos do `scraper.py`.
- Em vez de buscar na "Home", o "Scraper Multi-Source" mapeia **diretamente as categorias específicas**: `/noticias/`, `/concursos/` e `?s=editais`. Onde o conteúdo é preservado independentemente de geoblocking internacional.

### 7.4 Parágrafos não extraídos (Could not extract paragraph)

**Causa:** Layouts diferentes entre notícias do portal. Algumas usam classes CSS distintas.

**Resolução:**
- Implementados 5 seletores XPath em cascata para cobrir variações de layout.
- Reduzido o filtro de tamanho mínimo de 50 para 25 caracteres.

### 7.5 Permissão negada no push do GitHub Actions (HTTP 403)

**Erro:**
```
remote: Write access to repository not granted.
```

**Resolução:**
- Alteração em **Settings → Actions → General → Workflow permissions** para "Read and write permissions".

### 7.6 Notificação não entregue no Microsoft Teams

Este foi o problema mais complexo, composto por dois erros distintos que se manifestavam simultaneamente.

#### Problema A — Destino do chat inválido para o Flow Bot

**Erro no Power Automate:**
```
LocationLookupFailed — Location lookup failed for thread 19:preview-...
```

**Causa:**
O fluxo foi configurado para postar como `Flow bot` em um `Group chat`. O ID do chat retornado (`19:preview-...`) indicava uma referência interna temporária ou de preview que o conector do Microsoft Graph não conseguia resolver para um destino válido de entrega.

Na prática:
- O chat escolhido no template ficou associado a uma referência interna inválida.
- O Flow bot não conseguiu mapear o `threadId` para um destino de entrega.
- O webhook aceitava a requisição (HTTP 200), mas a mensagem morria na etapa final do fluxo.

**Resolução:**
Alteração da identidade de postagem de **"Flow bot"** para **"Usuário"**. Isso fez a postagem usar a conexão e autorização do próprio usuário no Teams, em vez da identidade do bot. Além disso, o chat foi reconfigurado no fluxo, removendo a dependência do `threadId` problemático.

#### Problema B — Formato do Adaptive Card incompatível com a ação do Power Automate

**Erro no Power Automate:**
```
InvalidBotAdaptiveCard — Property 'type' must be 'AdaptiveCard'
```

**Causa:**
A ação `Post card in a chat or channel` do Power Automate não espera receber o payload completo do webhook. Ela espera receber **somente o objeto do Adaptive Card** (o conteúdo de `attachments[0].content`), não o envelope `{"type": "message", "attachments": [...]}`.

Na configuração do fluxo, o campo "Cartão Adaptável" estava sendo alimentado com uma expressão inadequada que passava o valor em formato incompatível (em alguns casos usando `string(...)`, que convertia o objeto em texto).

**Resolução:**

No **Python** (`notifier.py`): o payload foi mantido no formato correto com `attachments`, onde `content` contém o objeto do Adaptive Card real:
```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": { "type": "AdaptiveCard", ... }
  }]
}
```

No **Power Automate**: o campo "Cartão Adaptável" foi configurado para apontar para:
```
first(variables('Attachments'))?['content']
```
Isso garante que a ação receba exatamente o objeto do card, sem envelope extra e sem serialização indevida.

---

## 8. Configuração Inicial

### 8.1 Google Gemini
1. Acesse [Google AI Studio](https://aistudio.google.com/).
2. Gere uma API Key.
3. Salve no secret `GEMINI_API_KEY` do repositório GitHub.

### 8.2 Microsoft Teams (Power Automate Workflow)
1. No Teams, abra o app **Fluxos de trabalho** (Workflows).
2. Crie um fluxo a partir do modelo "Postar em um chat quando uma solicitação de webhook for recebida".
3. Configure:
   - **Postar como:** Usuário (não Flow bot).
   - **Chat:** Selecione o chat de destino desejado.
4. No editor avançado do fluxo, configure o campo "Cartão Adaptável" com a expressão: `first(variables('Attachments'))?['content']`.
5. Copie a URL gerada do webhook e salve no secret `TEAMS_WEBHOOK_URL` do repositório GitHub.

### 8.3 GitHub Actions
1. Vá em **Settings → Actions → General → Workflow permissions**.
2. Selecione **"Read and write permissions"**.
3. Salve.

### 8.4 Teste
1. Vá na aba **Actions** do repositório.
2. Selecione o workflow "Monitor de Editais de Residência Médica".
3. Clique em **"Run workflow"** para executar manualmente e validar o fluxo completo.

---

## 9. Considerações de Produção

- **Alta Performance:** Ao eliminar totalmente a filtragem de IA e chamadas externas desnecessárias, o monitor roda em menos de 5 segundos, sem delays artificiais (`time.sleep`).
- **Fuso Horário:** O agendamento cron no GitHub Actions está em UTC. As conversões para BRT (UTC-3) foram aplicadas.
- **Deduplicação Composta:** A persistência via `last_seen.json` (commitado no repositório) garante que apenas editais novos ou modificações/retificações gerem novos alertas.
- **Custo e Cota:** Zero. Sem taxas de API, sem chaves do Gemini, 100% gratuito utilizando a infraestrutura nativa do GitHub Actions e do Microsoft Teams.
