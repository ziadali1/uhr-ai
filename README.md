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
│           (banco vetorial — RAG por usuário)          │
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
- **Azure AI Search** — Banco vetorial com namespace por usuário (RAG)
- **Azure AI Foundry** — Orquestração do LLM (Claude / GPT-4)
- **Azure Blob Storage** — Armazenamento seguro de documentos

### Auth & Dados
- **Supabase Auth** — Autenticação simplificada
- **PostgreSQL (Supabase)** — Metadados e perfis de usuário

---

## 🔒 Anonimização Automática

Todo documento passa por um pipeline de anonimização antes de ser armazenado:

```
Upload → OCR (Document Intelligence)
       → Text Analytics detecta: nomes, CPFs, CRMs, endereços
       → Substitui por tokens: [PACIENTE], [MÉDICO], [DOCUMENTO]
       → Salva versão anonimizada no Blob Storage
       → Arquivo original descartado
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

> 💡 **Autenticação real (Supabase) é implementada apenas na Fase 5.**  
> Durante o desenvolvimento, um usuário mock local é utilizado para agilizar os testes.

### ✅ Fase 1 — Ambiente e Upload
- [ ] Setup do ambiente local (Python, Node.js, Git)
- [ ] Criar repositório no GitHub
- [ ] Setup do projeto (Next.js + FastAPI)
- [ ] Usuário mock local para desenvolvimento (`utils/auth.py`)
- [ ] Upload de documentos (PDF, imagem)
- [ ] OCR com Azure Document Intelligence
- [ ] Pipeline de anonimização automática
- [ ] Armazenamento no Azure Blob Storage

### 🔄 Fase 2 — RAG e Agente
- [ ] Indexação vetorial no Azure AI Search
- [ ] Namespace isolado por usuário
- [ ] Integração com Azure AI Foundry (LLM)
- [ ] Chat funcional com citação de fontes do histórico

### 🔄 Fase 3 — Análise e Direcionamento
- [ ] Extração de entidades com Text Analytics for Health
- [ ] Geração de resumo do caso pelo agente
- [ ] Hipóteses diagnósticas com disclaimer obrigatório
- [ ] Sugestão de especialidades médicas

### 🔄 Fase 4 — Modo Emergência
- [ ] Página pública acessível sem login (QR Code)
- [ ] Alertas automáticos de interações medicamentosas
- [ ] Cartão imprimível em PDF
- [ ] Link compartilhável com familiares

### 🔄 Fase 5 — Autenticação e Polimento
- [ ] Integração real com Supabase Auth
- [ ] Substituição do mock user por autenticação real
- [ ] Deploy completo no Azure
- [ ] Demo com dados anonimizados reais
- [ ] Vídeo de demonstração para portfólio

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
git clone https://github.com/seu-usuario/healthai.git
cd healthai

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
healthai/
├── frontend/                  # Next.js App
│   ├── app/
│   │   ├── dashboard/         # Painel do paciente
│   │   ├── emergency/         # Página pública de emergência
│   │   ├── chat/              # Interface do agente IA
│   │   └── upload/            # Upload de documentos
│   └── components/
│       ├── ui/                # shadcn/ui components
│       ├── emergency/         # Componentes do modo emergência
│       ├── chat/              # Componentes do chat
│       └── upload/            # Componentes de upload
│
├── backend/                   # Azure Functions (Python)
│   ├── api/                   # Endpoints REST
│   ├── services/
│   │   ├── azure/             # Integrações Azure
│   │   ├── rag/               # Pipeline RAG
│   │   └── anonymizer/        # Anonimização de documentos
│   ├── models/                # Schemas Pydantic
│   └── utils/                 # Utilitários
│
└── docs/                      # Documentação adicional
    ├── architecture.md
    ├── azure-setup.md
    └── demo-data.md
```

---

## 📜 Certificações Relacionadas

- Microsoft Azure AI Fundamentals (AI-900)
- Microsoft Azure AI Engineer Associate (AI-102)

---

## 👤 Autor

Desenvolvido como projeto de conclusão e portfólio prático das certificações Microsoft Azure AI.
