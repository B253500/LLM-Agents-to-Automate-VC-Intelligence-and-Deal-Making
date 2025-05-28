┌──────────────────┐
│  Front-end / UI │  
└────────┬─────────┘
         │ REST / CLI
┌────────▼─────────┐                 ┌──┐
│  Orchestration  │                │  External Data Sources │
│  layer (CrewAI) │──cal tools─>|  Ne  │  • News / Stat  |ista APIs  │
└────────┬─               |  │  • LinkedIn scraper      │
         │                          └────────────┬────────────┘
         │                                       │
┌────────▼────  adds/queries        │
│  LLM Chains     │◄────── store─────────┘
│  (LangChain/    │
│   LangGraph)    │
└────────┬─────────┘
         │ returns StartupProfile
┌────────▼─────────┐
│  Postgres /     │  
│  Vector DB      │   
└──────────────────┘

