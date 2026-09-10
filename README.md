# 🏥 Unified Health Record - UHR 

> Projeto de portfólio desenvolvido como aplicação prática das certificações **Microsoft Azure AI**.  
> Centraliza históricos médicos, analisa padrões com IA de casos complexos com muitos diagnósticos e gera relatórios de emergência acessíveis via QR Code.

---

## ⚠️ Aviso Legal

Este projeto é estritamente **educacional e de portfólio**. Não está disponível para uso público.  
As sugestões geradas pela IA **não constituem diagnóstico médico**. Toda informação deve ser validada por um profissional de saúde habilitado.  
Os dados utilizados nas demonstrações são **reais e anonimizados**, com consentimento do titular.

---

## 🎯 O Problema

Pacientes com históricos médicos complexos enfrentam barreiras diárias:
- Informações fragmentadas em laudos, receitas e exames físicos
- Dificuldade em saber qual especialista procurar
- Em emergências, familiares não conseguem comunicar alergias e medicamentos em uso
- Médicos de plantão atendem sem qualquer contexto do paciente

---

## 🧩 Os 5 Pilares

| Pilar | Função |
|---|---|
| 📁 **Memória** | Centraliza e organiza todos os documentos médicos |
| 🧠 **Análise** | Extrai entidades, cruza dados e identifica padrões |
| 🧭 **Direcionamento** | Sugere especialidades e levanta hipóteses diagnósticas |
| 🚨 **Emergência** | Relatório crítico instantâneo via QR Code |
| 💬 **Agente** | Responde perguntas em tempo real citando o histórico |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│              Next.js + Tailwind + shadcn/ui             │
│              Azure Static Web Apps (deploy)             │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                     BACKEND                             │
│               Azure Functions (Python)                  │
└────┬──────────────┬───────────────┬─────────────────────┘
     │              │               │
┌────▼────┐   ┌─────▼─────┐  ┌─────▼──────────────────┐
│  Azure  │   │   Azure   │  │     Azure AI Foundry    │
│  Blob   │   │ Document  │  │  Text Analytics for     │
│ Storage │   │Intelligence│  │  Health + LLM (Claude) │
└────┬────┘   └─────┬─────┘  └─────┬──────────────────┘
     │              │               │
┌────▼──────────────▼───────────────▼──────────────────┐
│                  Azure AI Search                      │
│           (busca por keyword — RAG por usuário)       │
└───────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   Supabase                          │
│              Auth + Metadados do usuário            │
└─────────────────────────────────────────────────────┘
```

---

## 🔬 Stack Técnica

### Frontend
- **Next.js 14** — App Router, SSR, responsivo (mobile-first)
- **Tailwind CSS** — Estilização utilitária
- **shadcn/ui** — Componentes acessíveis e profissionais

### Backend
- **Azure Functions** (Python 3.11) — Serverless, escalável
- **FastAPI** — Roteamento local para desenvolvimento

### Azure Services
- **Azure Document Intelligence** — OCR de PDFs e imagens de laudos
- **Azure Text Analytics for Health** — Extração de entidades médicas (diagnósticos, medicamentos, sintomas, procedimentos)
- **Azure AI Search** — Busca full-text com namespace por usuário (RAG)
- **Azure AI Foundry** — Orquestração do LLM (Claude)
- **Azure Blob Storage** — Armazenamento seguro de documentos

### Auth & Dados
- **Supabase Auth** — Autenticação com JWT
- **PostgreSQL (Supabase)** — Metadados e perfis de usuário

---

## 🔬 Pipeline de Processamento de Documentos

Todo documento passa por um pipeline híbrido de 3 camadas:

```
Upload → OCR (Document Intelligence) → texto bruto
       → Classificador (regex + LLM fallback)
         → família: structured_lab | imaging_narrative |
                    clinical_narrative | medication_document
       → Limpeza estrutural
         → separa metadados administrativos (CPF, CRM, endereço)
         → preserva apenas o texto clínico
       → Extração estruturada via LLM (por família)
         → achados, flags, resumo clínico, entidades para memória
       → Arquivo original salvo no Blob Storage (acessível na UI)
       → Indexação no Azure AI Search (RAG por usuário)
```

---

## 🚨 Modo Emergência — QR Code

Cada paciente possui uma página pública acessível por QR Code, **sem necessidade de login**.

**Disponível em:**
- 🔒 Tela de bloqueio do celular
- 🖨️ Cartão físico imprimível (PDF gerado pelo app)
- 📲 Link compartilhável com familiares

**O que exibe:**
```
┌──────────────────────────────────────┐
│  🚨 EMERGÊNCIA — [PACIENTE]          │
│  🩸 Tipo Sanguíneo: A+               │
│                                      │
│  ⚠️ ALERGIAS                         │
│  • Dipirona (reação severa)          │
│  • Penicilina                        │
│                                      │
│  💊 MEDICAMENTOS EM USO              │
│  • Warfarina 5mg ⚠️ risco cirúrgico  │
│  • Metformina 850mg                  │
│                                      │
│  🏥 CONDIÇÕES ATIVAS                 │
│  • Diabetes tipo 2                   │
│  • Fibrilação atrial                 │
│                                      │
│  [ VER HISTÓRICO COMPLETO ↓ ]        │
└──────────────────────────────────────┘
```

---

## 💬 Agente IA — RAG por Paciente

O agente combina conhecimento médico geral da LLM com dados específicos do paciente via RAG:

```
Pergunta: "Esse paciente pode receber Heparina?"
        ↓
Azure AI Search busca nos documentos do paciente
        ↓
Recupera: laudo cardíaco, lista de medicamentos, alergias
        ↓
Prompt injetado com contexto do paciente
        ↓
Resposta: "⚠️ Paciente em uso de Warfarina desde 2021.
           Heparina combinada aumenta risco hemorrágico.
           📎 Fonte: Laudo cardiológico 03/2024"
```

Cada usuário tem seu **namespace isolado** no Azure AI Search — privado, seguro e sem custo adicional por usuário.

---

## 📅 Plano de Desenvolvimento

### ✅ Fase 1 — Ambiente e Upload
- [x] Setup do ambiente local (Python, Node.js, Git)
- [x] Criar repositório no GitHub
- [x] Setup do projeto (Next.js + Azure Functions / FastAPI)
- [x] Upload de documentos (PDF, imagem)
- [x] OCR com Azure Document Intelligence
- [x] Armazenamento no Azure Blob Storage (arquivo original + texto OCR)

### ✅ Fase 2 — RAG e Agente IA
- [x] Indexação no Azure AI Search (keyword/BM25, namespace por usuário)
- [x] Namespace isolado por usuário
- [x] Integração com LLM (Claude via Azure AI Foundry)
- [x] Chat funcional com citação de fontes do histórico

### ✅ Fase 2b — Pipeline Híbrido de Documentos *(novo)*
- [x] Classificador de família documental (structured_lab, imaging_narrative, clinical_narrative, medication_document)
- [x] Fallback LLM no classificador para documentos ambíguos
- [x] Limpeza estrutural — separação de metadados administrativos do texto clínico
- [x] Extração estruturada via LLM por família (achados, flags, resumo clínico)
- [x] Entidades clínicas derivadas do resultado estruturado

### ✅ Fase 2c — Centralização e Visualização de Documentos *(novo)*
- [x] Label de tipo documental na lista (laboratório, imagem, nota clínica, prescrição)
- [x] Armazenamento e visualização do arquivo original (PDF/imagem) na UI
- [x] Visualização estruturada por família (tabela de achados, laudo de imagem, nota clínica, prescrição)
- [x] Resumo clínico automático exibido na lista de documentos

### ✅ Fase 2d — Perfil de Saúde Manual (/saude) *(novo)*
- [x] Entrada manual: medicamentos em uso, queixas recentes, alergias
- [x] CRUD completo com persistência no Supabase
- [x] Sincronização automática com o RAG após cada alteração

### ⚠️ Fase 3 — Análise e Direcionamento *(parcial)*
- [x] Resumo clínico automático por documento (via extrator LLM)
- [x] Agregação de entidades e sugestão de especialidades médicas (mock)
- [ ] Análise consolidada do caso via LLM em produção (`_llm_analysis` não implementado)
- [ ] Hipóteses diagnósticas com disclaimer obrigatório

### ✅ Fase 4 — Modo Emergência
- [x] Página pública acessível sem login (`/emergency?userId=...`)
- [x] QR Code gerado dinamicamente (PNG)
- [x] Cartão de emergência imprimível em PDF (A5)
- [x] Exibe: tipo sanguíneo, alergias (com severidade), medicamentos, condições ativas

### ✅ Fase 5 — Autenticação e Deploy
- [x] Integração real com Supabase Auth (JWT)
- [x] Deploy backend no Azure Functions
- [x] Deploy frontend no Azure Static Web Apps
- [ ] Vídeo de demonstração para portfólio

### ❌ Pendente / Backlog
- Análise consolidada via LLM em produção (Fase 3)
- Exclusão de documentos do histórico
- Busca semântica com embeddings (atual: keyword BM25)
- Comparação temporal de exames (ex: evolução de TSH ao longo do tempo)
- Correção de bug: `chat.py` sem tratamento de exceções (erro 500 em produção)
- Correção de bug: `extractor.py` sem logging de falhas silenciosas

---

## 💰 Custo Estimado (Portfólio)

| Serviço | Tier | Custo |
|---|---|---|
| Azure Functions | Consumption | Gratuito (1M req/mês) |
| Azure Blob Storage | LRS | ~$0.02/GB |
| Azure Document Intelligence | F0 Free | 500 páginas/mês grátis |
| Text Analytics for Health | S tier | ~$0.003/registro |
| Azure AI Search | Basic | ~$25/mês |
| Azure AI Foundry (LLM) | Pay-per-use | ~$5–15 total |
| Supabase | Free tier | Gratuito |
| Azure Static Web Apps | Free | Gratuito |

**Total estimado para desenvolvimento: ~$30–50**

---

## 🚀 Como Rodar Localmente

```bash
# Clone o repositório
git clone https://github.com/ziadali1/uhr-ai.git
cd uhr-ai

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # preencha as variáveis Azure
uvicorn main:app --reload

# Frontend
cd ../frontend
npm install
cp .env.local.example .env.local  # preencha as variáveis
npm run dev
```

---

## 📁 Estrutura do Projeto

```
uhr-ai/
├── frontend/                  # Next.js App
│   ├── app/
│   │   ├── dashboard/         # Painel do paciente
│   │   ├── emergency/         # Página pública de emergência (sem login)
│   │   ├── chat/              # Interface do agente IA
│   │   ├── saude/             # Perfil de saúde manual
│   │   └── upload/            # Upload de documentos
│   └── components/
│       ├── ui/                # shadcn/ui components
│       ├── chat/              # Componentes do chat
│       ├── health/            # Componentes do perfil de saúde
│       └── upload/            # Componentes de upload e visualização
│
├── backend/                   # Azure Functions (Python)
│   ├── api/                   # Endpoints REST
│   ├── services/
│   │   ├── azure/             # Integrações Azure
│   │   ├── pipeline/          # Classificador, limpeza e extrator
│   │   └── rag/               # Pipeline RAG
│   ├── models/                # Schemas Pydantic
│   └── utils/                 # Utilitários
│
└── docs/                      # Documentação adicional
```

---

## 📜 Certificações Relacionadas

- Microsoft Azure AI Fundamentals (AI-900)
- Microsoft Azure AI Engineer Associate (AI-102)

---

## 👤 Autor

Desenvolvido como projeto de conclusão e portfólio prático das certificações Microsoft Azure AI.
