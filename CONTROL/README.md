# Dashboard Financeiro IA Corrigido

Correção aplicada:

- O app agora localiza automaticamente qualquer arquivo `.xlsx` na pasta do projeto.
- Não depende mais do nome exato `dashboard_financeiro_avancado (1).xlsx`.
- Se houver mais de um Excel, ele prioriza o arquivo que contém `dashboard_financeiro` no nome.

No GitHub, deixe na raiz:

- app.py
- requirements.txt
- sua planilha .xlsx

Executar:

```bash
pip install -r requirements.txt
streamlit run app.py
```
