# Dashboard Financeiro IA - Correção Definitiva Excel

Correção aplicada:

- O app procura automaticamente qualquer arquivo `.xlsx`:
  - na mesma pasta do `app.py`;
  - em subpastas do projeto.
- Prioriza arquivos que contenham `dashboard_financeiro` no nome.
- Mostra na lateral qual Excel foi carregado.
- Se não encontrar, mostra a lista real de arquivos encontrados no Streamlit Cloud.

No GitHub, deixe na raiz ou em qualquer pasta do projeto:

- app.py
- requirements.txt
- sua planilha .xlsx

Executar:

```bash
pip install -r requirements.txt
streamlit run app.py
```
