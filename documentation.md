# Alerta de Editais — Documentação Técnica

> Última atualização: 2026-09-22  
> Versão: 0.4  
> Repositório: `cadeteafya/alerta-editais`

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Estrutura de arquivos](#3-estrutura-de-arquivos)
4. [Módulos](#4-módulos)
5. [Cartão Microsoft Teams](#5-cartão-microsoft-teams)
6. [Deduplicação e estado](#6-deduplicação-e-estado)
7. [GitHub Actions](#7-github-actions)
8. [Secrets](#8-secrets)
9. [Configuração inicial](#9-configuração-inicial)
10. [Diagnóstico de problemas](#10-diagnóstico-de-problemas)

---

## 1. Visão geral

Sistema automatizado que monitora a página publicada do **Edital Tracker** ([edital-tracker-woad.vercel.app](https://edital-tracker-woad.vercel.app/)) e envia notificações estruturadas ao Microsoft Teams via Adaptive Cards quando um novo edital é detectado.

**Stack:**

| Componente | Tecnologia |
|---|---|
| Orquestração | GitHub Actions (cron schedule + workflow_dispatch) |
| Scraper | Python 3.11 (`requests` + `lxml`) |
| Notificação | Microsoft Teams — Power Automate Webhook |
| Persistência de estado | `data/last_seen.json` (commitado no repositório) |

---

## 2. Arquitetura

```
┌───────────────────┐
│  GitHub Actions   │  ← cron: mesma janela do edital-tracker
│  (monitor.yml)    │
└────────┬──────────┘
         │ executa
         ▼
┌───────────────────┐     GET HTML      ┌─────────────────────────────────┐
│    src/main.py    │ ─────────────────▶│  edital-tracker-woad.vercel.app │
│  (orquestrador)   │                   │  (Next.js SSR — fonte de dados) │
└────────┬──────────┘                   └─────────────────────────────────┘
         │
         ├── scraper.py   → extrai editais do HTML via XPath
         │
         ├── compara com data/last_seen.json
         │
         └── notifier.py  → POST webhook → Power Automate → Teams
                                │
                                ▼
                        ┌───────────────┐
                        │  Microsoft    │
                        │  Teams Chat   │
                        │ (Adaptive     │
                        │  Card v1.4)   │
                        └───────────────┘
```

---

## 3. Estrutura de arquivos

```
alerta-editais/
├── .github/
│   └── workflows/
│       └── monitor.yml          # GitHub Actions — cron + dispatch manual
├── data/
│   └── last_seen.json           # Estado: chaves de editais já notificados
├── src/
│   ├── main.py                  # Orquestrador principal
│   ├── scraper.py               # Web scraper do Edital Tracker
│   └── notifier.py              # Montagem e envio do Adaptive Card ao Teams
├── requirements.txt
├── README.md
└── documentation.md             # Este arquivo
```

---

## 4. Módulos

### 4.1 `src/scraper.py` — `fetch_articles()`

Faz GET na homepage do Edital Tracker e extrai todos os `<article>` via XPath (lxml).

**Campos extraídos por edital:**

| Campo | Descrição | XPath (resumido) |
|---|---|---|
| `title` | Título reescrito do edital | `//h3/text()` |
| `institution` | Nome curto da instituição | Span no div com `linear-gradient` |
| `year` | Ano do processo | Span com `font-mono text-white` |
| `tag` | Status ("Saiu o edital", etc.) | Primeiro span com `tracking-wider` |
| `published_at` | Data de publicação formatada | `//header/p/span//text()` |
| `next_milestone` | `{stage, date, time_left}` — próximo marco | Div `bg-[var(--surface-muted)]` |
| `schedule` | Lista `[{stage, date}]` — cronograma completo | `//ol/li` — span[1] e span[2] |
| `official_link` | URL do site oficial | `//a[contains(text(), 'Site oficial')]/@href` |
| `fee` | Taxa de inscrição | `//span[normalize-space(text())='Taxa']/following-sibling::span[1]/text()` |
| `link` | Chave de deduplicação | `f"{title} \| {pub_date}"` |

> **`fee`**: se o span "Taxa" não existir no card (card sem taxa), o fallback é a string `"Confirmar"`.

**Chave de deduplicação:**
```python
unique_key = f"{title} | {pub_date}"
```

### 4.2 `src/notifier.py` — `send_teams_notification(edital)`

Monta e envia um Adaptive Card v1.4 via POST para o webhook do Power Automate.

**Lógica do cabeçalho:**

```python
is_new_edital = "SAIU" in tag.upper() or "NOVO" in tag.upper() or "EDITAL" in tag.upper()
card_header = "🚨 NOVO EDITAL: {sigla} {ano}"  # estilo Attention (vermelho)
# ou
card_header = "🔔 ATUALIZAÇÃO: {sigla} {ano}"  # estilo Accent (azul)
```

**Seções do payload:**

1. Container cabeçalho (Attention/Accent) com título do card.
2. TextBlock com o título completo do edital.
3. FactSet com metadados: `🏥 Instituição`, `📅 Publicado em`, `💰 Taxa`.
4. Container "próximo marco" (accent) — condicional, só se existir.
5. TextBlock "Cronograma" + FactSet com as datas (limite de 10 linhas; excedente vira aviso).
6. Actions: botão "🌐 ACESSAR SITE OFICIAL" (condicional) + "📋 VER NO EDITAL TRACKER".

**Formato do payload para o Power Automate:**

```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.4",
      "body": [...],
      "actions": [...]
    }
  }]
}
```

### 4.3 `src/main.py` — `run()`

```
1. load_state()  →  dict de chaves já notificadas  (data/last_seen.json)
2. fetch_articles()  →  lista de editais do site
3. Para cada edital:
   ├── Se link ∈ seen_links  →  skip
   └── send_teams_notification(edital)
       └── Se sucesso: adiciona link ao novo estado
4. save_state()  →  commita data/last_seen.json
```

---

## 5. Cartão Microsoft Teams

Visualização do Adaptive Card enviado ao Teams:

```
┌─────────────────────────────────────────────────┐
│  🚨 NOVO EDITAL: {SIGLA} {ANO}                 │  ← fundo vermelho (Attention)
├─────────────────────────────────────────────────┤
│  {Título completo do edital}                    │
├─────────────────────────────────────────────────┤
│  🏥 Instituição    │  {nome}                    │
│  📅 Publicado em  │  {data}                    │  ← FactSet
│  💰 Taxa          │  {R$ 800 ou Confirmar}      │
├─────────────────────────────────────────────────┤
│  🚀 PRÓXIMO MARCO EM DESTAQUE                  │  ← Container azul (condicional)
│  {Etapa}    │  {Data} (em N dias)              │
├─────────────────────────────────────────────────┤
│  📅 Cronograma - Principais datas:             │
│  {Etapa 1}  │  {Data 1}                        │
│  {Etapa 2}  │  {Data 2}                        │  ← FactSet (máx. 10 linhas)
│  ...                                            │
├─────────────────────────────────────────────────┤
│  [ 🌐 ACESSAR SITE OFICIAL ]                   │
│  [ 📋 VER NO EDITAL TRACKER ]                  │  ← Botões de ação
└─────────────────────────────────────────────────┘
```

---

## 6. Deduplicação e estado

**Chave única = `"Título do Edital | Data de Publicação"`**

O `data/last_seen.json` armazena um dict `{chave: título}` de todos os editais já notificados:

```json
{
  "FAMERP abre seleção para Residência Médica 2027 | 22 de set. de 2026": "FAMERP abre seleção...",
  "PUC-SP 2027: prazo de inscrições... | 22 de set. de 2026": "PUC-SP 2027: prazo..."
}
```

**Regra de re-notificação:**

| O que muda no Edital Tracker | Chave muda? | Novo alerta? |
|---|---|---|
| `timeline`, `fee`, `officialUrl`, `updatedAt` | Não | Não |
| `originalTitle` / `rewrittenTitle` | Sim | Sim |
| `publishedAt` | Sim | Sim |

---

## 7. GitHub Actions

Arquivo: `.github/workflows/monitor.yml`

| Janela | Frequência |
|---|---|
| Seg–Sex, 08h–18h BRT | A cada 30 minutos |
| Sáb e Dom | Uma vez às 13h BRT |
| Manual | `workflow_dispatch` |

Ao final da execução, o workflow commita `data/last_seen.json` se ele foi atualizado (novos alertas enviados), usando a identidade `action@github.com`.

**Permissão necessária:** Settings → Actions → General → Workflow permissions → "Read and write permissions".

---

## 8. Secrets

Configurados em: **Settings → Secrets and variables → Actions → Repository secrets**

| Secret | Obrigatório | Descrição |
|---|---|---|
| `TEAMS_WEBHOOK_URL` | Sim | URL gerada pelo fluxo Power Automate no Teams |

---

## 9. Configuração inicial

### 9.1 Power Automate (Microsoft Teams Workflow)

1. No Teams, abra o app **Fluxos de trabalho** (Workflows).
2. Crie um fluxo a partir do modelo **"Postar em um chat quando uma solicitação de webhook for recebida"**.
3. Configure:
   - **Postar como:** Usuário (não "Flow bot" — o bot causa erro `LocationLookupFailed`).
   - **Chat:** selecione o chat de destino.
4. No editor avançado, configure o campo "Cartão Adaptável" com a expressão:
   ```
   first(variables('Attachments'))?['content']
   ```
   Isso extrai o objeto do Adaptive Card do envelope `attachments[0].content`.
5. Copie a URL do webhook e salve no secret `TEAMS_WEBHOOK_URL`.

### 9.2 GitHub Actions

1. Adicione o secret `TEAMS_WEBHOOK_URL` ao repositório.
2. Vá em **Settings → Actions → General → Workflow permissions** → "Read and write permissions".
3. Para testar, vá em **Actions → Monitor de Editais → Run workflow**.

---

## 10. Diagnóstico de problemas

### Notificação não chega ao Teams

**Causa A:** URL do webhook expirada ou inválida.  
**Resolução:** regenerar o fluxo no Power Automate e atualizar o secret.

**Causa B:** Fluxo configurado para postar como "Flow bot".  
**Resolução:** alterar para "Usuário" (ver seção 9.1). O Flow bot causa `LocationLookupFailed`.

**Causa C:** Campo "Cartão Adaptável" recebe o envelope completo ao invés do `content`.  
**Resolução:** usar a expressão `first(variables('Attachments'))?['content']` no Power Automate.

### Taxa aparece como "Confirmar" no cartão

**Causa:** o card do Edital Tracker não continha o campo taxa no HTML quando o alerta foi gerado (edital capturado antes da adição do campo `fee`).

**Situação atual:** o campo `fee` é renderizado pelo Next.js no HTML do Edital Tracker. O `scraper.py` usa o XPath `//span[normalize-space(text())='Taxa']/following-sibling::span[1]/text()` para extraí-lo. Se o card mostrar "Confirmar", significa que o JSON do `edital-tracker` também não tem a taxa: não estava no artigo original **nem** pôde ser lida com segurança do PDF do edital (fallback `pdf_fee.py`, desde v0.6 do edital-tracker). O fallback deixa "Confirmar" de propósito quando há mais de um edital na página ou mais de um valor de taxa (sócio/não sócio, por programa etc.).

### Push rejeitado pelo GitHub Actions (403)

**Causa:** permissão de workflow insuficiente.  
**Resolução:** Settings → Actions → General → Workflow permissions → "Read and write permissions".

### Edital já notificado sendo re-notificado

**Causa:** o título ou a data de publicação mudou no Edital Tracker (nova chave de dedup).  
**Isso é comportamento esperado** para retificações formais que alteram título ou data.
