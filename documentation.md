# Alerta de Editais — Documentação Técnica

## 1. Visão Geral

Sistema automatizado de custo zero que monitora o portal [Estratégia MED](https://med.estrategia.com/portal/?s=editais) em busca de novos editais de residência médica e envia notificações em tempo real para o Microsoft Teams via Adaptive Cards.

**Stack:**

| Componente       | Tecnologia                                      |
| ---------------- | ------------------------------------------------ |
| Orquestração     | GitHub Actions (cron schedule + workflow_dispatch) |
| Scraper          | Python 3.11 (`requests` + `lxml`)                |
| Filtro Semântico | Google Gemini 2.5 Flash (via `google-genai` SDK) |
| Notificação      | Microsoft Teams (Power Automate Webhook)         |
| Persistência     | `data/last_seen.json` (commitado no repositório) |

---

## 2. Arquitetura

```
┌──────────────┐      ┌────────────────┐      ┌──────────────┐      ┌─────────────┐
│ GitHub Action │─────▶│  scraper.py    │─────▶│ ai_filter.py │─────▶│ notifier.py │
│  (cron job)  │      │ Extrai artigos │      │ Gemini 2.5   │      │ Webhook POST│
└──────────────┘      └────────────────┘      └──────────────┘      └──────┬──────┘
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
3. `scraper.py` faz uma requisição HTTP à página de busca do portal e extrai os artigos via XPath.
4. Para cada artigo novo (não presente no `last_seen.json`), o scraper busca o resumo da notícia (via meta tag `og:description` ou parágrafos do HTML).
5. O título e o resumo são enviados ao `ai_filter.py`, que chama a API do Gemini 2.5 Flash para classificar se o conteúdo é um edital de residência médica.
6. Se confirmado como edital, `notifier.py` envia um POST com Adaptive Card para o Webhook do Power Automate no Teams.
7. `main.py` salva o novo estado no `last_seen.json` e o GitHub Actions commita o arquivo atualizado de volta no repositório.

---

## 3. Estrutura de Arquivos

```
alerta-editais/
├── .github/
│   └── workflows/
│       └── monitor.yml          # Configuração do GitHub Actions
├── data/
│   └── last_seen.json           # Estado persistido (links já processados)
├── src/
│   ├── main.py                  # Orquestrador principal
│   ├── scraper.py               # Web scraper do portal Estratégia MED
│   ├── ai_filter.py             # Filtro de classificação via Gemini
│   └── notifier.py              # Envio de notificações para o Teams
├── requirements.txt             # Dependências Python
├── README.md                    # Instruções de configuração
└── documentation.md             # Este documento
```

---

## 4. Módulos

### 4.1 `src/scraper.py`

Responsável pela extração de dados do portal Estratégia MED.

**`fetch_articles()`**
- Faz GET sequencial em múltiplas fontes (atualmente a Home `https://med.estrategia.com/portal/` e a Busca de Editais `https://med.estrategia.com/portal/?s=editais`) com headers de User-Agent simulando navegador.
  - *Sempre extraímos da Home porque editais grandes como Revalida e CNU aparecem como Destaques lá mas demoram a indexar na busca.*
- Parseia o HTML com `lxml` e extrai todos os elementos `<article>`.
- De cada artigo extrai: título (`<h2><a>` ou `<h3><a>`), link (`href`) e data (`<time datetime>`).
- Mantém um Set (`seen_urls`) interno durante a execução para resolver duplicações instantâneas (ex: mesmo edital listado na Home e na Busca).
- Retorna lista de dicionários `[{"title", "link", "date"}]`.

**`fetch_article_paragraph(url)`**
- Faz GET na URL do artigo individual com header `Referer` apontando para a página de busca (evita bloqueio 403 Forbidden).
- Estratégia de extração em cascata:
  1. **Meta tag `og:description`** — resumo embutido no HTML, confiável e nunca bloqueado.
  2. **XPath em 5 seletores** — `entry-content`, `ast-article-single`, `post-content`, `article`, `body` — em ordem de especificidade.
- Filtra parágrafos com mais de 25 caracteres para evitar legendas e botões.

### 4.2 `src/ai_filter.py`

Classificação semântica via Google Gemini.

- Usa o SDK moderno `google-genai` (não o pacote legado `google-generativeai`).
- **Modelo:** `gemini-2.5-flash` (Free Tier: limite de 5 requisições/minuto).
- Envia prompt estruturado pedindo resposta em JSON puro.
- Parseia a resposta removendo possíveis delimitadores markdown (` ```json `, ` ``` `).
- Retorna `{"is_edital": true/false, "instituicao": "...", "tipo": "..."}`.
- Possui fallback para `gemini-1.5-flash` caso o modelo principal falhe.

### 4.3 `src/notifier.py`

Envio de notificações para o Microsoft Teams.

- Monta um payload JSON contendo um Adaptive Card v1.4 dentro de `attachments`.
- O card contém:
  - Header com ícone de alerta e título em destaque.
  - FactSet com instituição e tipo de edital.
  - TextBlock com o resumo extraído do artigo.
  - Botão `Action.OpenUrl` com link direto para o edital completo.
- Envia via POST para a URL do Webhook armazenada no secret `TEAMS_WEBHOOK_URL`.

**Estrutura do payload enviado ao webhook:**
```json
{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
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
429 RESOURCE_EXHAUSTED — Quota exceeded: limit 5, model: gemini-2.5-flash
```

**Causa:** O Free Tier do `gemini-2.5-flash` permite apenas 5 requisições por minuto. Na primeira execução (com `last_seen.json` vazio), o sistema tentou processar ~15 artigos rapidamente.

**Resolução:**
- Adicionado `time.sleep(15)` entre cada artigo no loop de `main.py`.
- Em operação normal, o sistema processa 1–2 artigos novos por execução, ficando dentro do limite.

### 7.3 Scraper bloqueado pelo site (HTTP 403)

**Erro:**
```
403 Client Error: Forbidden for url: https://med.estrategia.com/portal/noticias/...
```

**Causa:** O portal Estratégia MED bloqueia requisições sem header `Referer` em páginas de artigo individual.

**Resolução:**
- Adicionado header `Referer: https://med.estrategia.com/portal/?s=editais` nas requisições de artigo.
- Implementada extração via meta tag `og:description` como estratégia primária (não depende do corpo HTML).

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

- **Rate Limit:** O `gemini-2.5-flash` no Free Tier permite 5 requisições por minuto. O delay de 15 segundos entre artigos garante conformidade. Em operação normal (1–2 artigos novos por execução), o limite não é atingido.
- **Fuso Horário:** O agendamento cron no GitHub Actions está em UTC. As conversões para BRT (UTC-3) foram aplicadas.
- **Deduplicação:** A persistência via `last_seen.json` (commitado no repositório) garante que artigos já processados não sejam reprocessados em execuções futuras.
- **Custo:** Zero. Todas as tecnologias utilizadas (GitHub Actions Free Tier, Gemini Free Tier, Power Automate no Teams) operam dentro dos limites gratuitos.
