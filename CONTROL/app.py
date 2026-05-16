import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import date

st.set_page_config(page_title="Dashboard Financeiro IA", page_icon="🤖", layout="wide")

ARQ_EXCEL = "dashboard_financeiro_avancado (1).xlsx"
ARQ_GASTOS = "novos_lancamentos.csv"
ARQ_STATUS = "status_planilha.csv"
ARQ_ENTRADAS = "entradas.csv"
MESES = ["JANEIRO","FEVEREIRO","MARÇO","ABRIL","MAIO","JUNHO","JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]
STATUS = ["TODOS", "NÃO", "PAGO", "CANCELAMENTO"]

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#020617,#0f172a,#111827)}
[data-testid="stSidebar"]{background:#020617}.stMetric{background:rgba(15,23,42,.82);border:1px solid rgba(148,163,184,.24);padding:14px;border-radius:18px;box-shadow:0 10px 28px rgba(0,0,0,.25)}
h1,h2,h3,p,label,span,div{color:#f8fafc}.ia-card{background:rgba(15,23,42,.9);border:1px solid rgba(148,163,184,.25);padding:20px;border-radius:20px;margin:12px 0;box-shadow:0 10px 28px rgba(0,0,0,.25)}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def ler_excel():
    df = pd.read_excel(ARQ_EXCEL, sheet_name="GASTOS")
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def moeda(v):
    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")

def plot(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,.25)", font=dict(color="#f8fafc"), margin=dict(l=20,r=20,t=48,b=20), legend=dict(orientation="h", y=1.05))
    return fig

def ler_csv(arq, cols):
    if Path(arq).exists():
        df = pd.read_csv(arq)
    else:
        df = pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df[cols]

def normaliza_status(df):
    if df.empty: return df
    if "Pago" in df.columns and "Status" not in df.columns: df = df.rename(columns={"Pago":"Status"})
    if "Status" not in df.columns: df["Status"] = "NÃO"
    df["Status"] = df["Status"].fillna("NÃO").astype(str).str.upper().str.strip().replace({"SIM":"PAGO","NAO":"NÃO","":"NÃO"})
    return df

def ler_status():
    return ler_csv(ARQ_STATUS, ["ID", "Status"])

def ler_gastos_app():
    cols = ["ID","Origem","Data","Cartão","Descrição","Categoria","Mês","Valor","Status"]
    df = ler_csv(ARQ_GASTOS, cols)
    if not df.empty:
        vazio = df["ID"].isna() | (df["ID"].astype(str).str.strip()=="")
        for i in df[vazio].index: df.loc[i,"ID"] = f"NOVO-{i+1}"
        df["Origem"] = df["Origem"].replace("","APP").fillna("APP")
    return normaliza_status(df)

def ler_entradas():
    df = ler_csv(ARQ_ENTRADAS, ["ID","Data","Descrição","Categoria","Mês","Valor"])
    if not df.empty:
        vazio = df["ID"].isna() | (df["ID"].astype(str).str.strip()=="")
        for i in df[vazio].index: df.loc[i,"ID"] = f"ENTRADA-{i+1}"
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Mês"] = df["Mês"].fillna("").astype(str).str.upper().str.strip()
    return df

def salvar(df, arq):
    df.to_csv(arq, index=False)

def prox_id(df, prefixo):
    nums=[]
    if not df.empty and "ID" in df.columns:
        for x in df["ID"].astype(str):
            if x.startswith(prefixo+"-"):
                try: nums.append(int(x.replace(prefixo+"-", "")))
                except: pass
    return f"{prefixo}-{max(nums)+1}" if nums else f"{prefixo}-1"

def base_planilha(df_excel):
    status_df = ler_status(); mapa = {}
    if not status_df.empty: mapa = dict(zip(status_df["ID"].astype(str), status_df["Status"].astype(str)))
    regs=[]
    for idx, l in df_excel.iterrows():
        for mes in MESES:
            if mes in df_excel.columns:
                valor = l.get(mes, 0)
                if pd.notna(valor) and valor != 0:
                    idv = f"EXCEL-{idx}-{mes}"
                    regs.append({"ID":idv,"Origem":"PLANILHA","Data":"","Cartão":l.get("CARTÃO",""),"Descrição":l.get("DESCRIÇÃO",""),"Categoria":l.get("CATEGORIA",""),"Mês":mes,"Valor":float(valor),"Status":mapa.get(idv,"NÃO")})
    return normaliza_status(pd.DataFrame(regs))

def montar_base(df_excel):
    df = pd.concat([base_planilha(df_excel), ler_gastos_app()], ignore_index=True)
    if df.empty: return df
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    for c,p in [("Cartão","NÃO INFORMADO"),("Descrição",""),("Categoria","SEM CATEGORIA"),("Mês","")]:
        df[c] = df[c].fillna(p).astype(str).str.strip()
    df["Mês"] = df["Mês"].str.upper()
    df = normaliza_status(df)
    return df

def opcoes(df_excel, df_app, col_excel, col_app, padrao):
    vals=[]
    if col_excel in df_excel.columns: vals += df_excel[col_excel].dropna().astype(str).str.strip().tolist()
    if col_app in df_app.columns: vals += df_app[col_app].dropna().astype(str).str.strip().tolist()
    vals = sorted(set([v for v in vals if v and v.upper() != "NAN"])) or [padrao]
    return vals + ["OUTRO / CADASTRAR NOVO"]

def atualizar_status(idv, origem, novo):
    if str(origem).upper()=="APP":
        df=ler_gastos_app(); df.loc[df["ID"].astype(str)==str(idv), "Status"] = novo; salvar(df, ARQ_GASTOS)
    else:
        df=ler_status(); df["ID"] = df["ID"].astype(str)
        if str(idv) in df["ID"].values: df.loc[df["ID"]==str(idv), "Status"] = novo
        else: df = pd.concat([df, pd.DataFrame([{"ID":str(idv),"Status":novo}])], ignore_index=True)
        salvar(df, ARQ_STATUS)

def saude(percentual, saldo):
    if saldo < 0: return "CRÍTICA", "O mês tende a fechar negativo. Reduza gastos ou marque cancelamentos necessários."
    if percentual <= 50: return "EXCELENTE", "Boa margem de sobra. Você pode reservar ou investir parte do saldo."
    if percentual <= 75: return "BOA", "O mês está positivo, mas acompanhe os maiores gastos."
    if percentual <= 90: return "ALERTA", "A renda está bastante comprometida. Reavalie gastos variáveis."
    return "CRÍTICA", "A renda está quase toda comprometida. Priorize controle imediato."

if not Path(ARQ_EXCEL).exists():
    st.error("Arquivo Excel não encontrado dentro da pasta do app."); st.code(ARQ_EXCEL); st.stop()

excel = ler_excel(); app_df = ler_gastos_app(); gastos = montar_base(excel); entradas = ler_entradas()

st.sidebar.title("🤖 Financeiro IA")
pagina = st.sidebar.radio("Menu", ["Painel IA", "Dashboard", "Adicionar Novos Valores", "Entradas / Receitas", "Análise Financeira do Mês", "Buscar / Atualizar Gastos", "Base de Dados"])
st.sidebar.caption("Gráficos renderizados + diagnóstico automático")

if pagina == "Painel IA":
    st.title("🤖 Painel IA Financeiro")
    mes = st.selectbox("Mês de análise", MESES)
    gm = gastos[(gastos["Mês"]==mes) & (gastos["Status"]!="CANCELAMENTO")].copy()
    em = entradas[entradas["Mês"]==mes].copy()
    ent = em["Valor"].sum() if not em.empty else 0
    sai = gm["Valor"].sum() if not gm.empty else 0
    pago = gm.loc[gm["Status"]=="PAGO","Valor"].sum() if not gm.empty else 0
    pend = gm.loc[gm["Status"]=="NÃO","Valor"].sum() if not gm.empty else 0
    saldo = ent - sai; perc = (sai/ent*100) if ent>0 else 0
    cl, rec = saude(perc, saldo)
    a,b,c,d,e = st.columns(5)
    a.metric("Entradas", moeda(ent)); b.metric("Gastos", moeda(sai)); c.metric("Saldo", moeda(saldo)); d.metric("% comprometido", f"{perc:.1f}%"); e.metric("Classificação", cl)
    st.markdown(f'<div class="ia-card"><h3>🧠 Diagnóstico IA</h3><p><b>{cl}</b> — {rec}</p><p>Pago: {moeda(pago)} | Pendente: {moeda(pend)}</p></div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=perc, title={"text":"% da renda comprometida"}, gauge={"axis":{"range":[0,120]},"bar":{"color":"#38bdf8"},"steps":[{"range":[0,50],"color":"#14532d"},{"range":[50,75],"color":"#713f12"},{"range":[75,100],"color":"#7f1d1d"},{"range":[100,120],"color":"#450a0a"}] }))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=360)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        resumo=pd.DataFrame({"Indicador":["Entradas","Gastos","Saldo"],"Valor":[ent,sai,saldo]})
        st.plotly_chart(plot(px.bar(resumo,x="Indicador",y="Valor",text_auto=".2f",title="Entradas x Gastos x Saldo")), use_container_width=True)
    c3,c4=st.columns(2)
    with c3:
        top=gm.sort_values("Valor",ascending=False).head(10)
        if top.empty: st.info("Sem gastos no mês.")
        else:
            fig=px.bar(top,x="Valor",y="Descrição",color="Categoria",orientation="h",text_auto=".2f",title="🔥 Maiores gastos")
            fig.update_layout(yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(plot(fig), use_container_width=True)
    with c4:
        cat=gm.groupby("Categoria",as_index=False)["Valor"].sum().sort_values("Valor",ascending=False)
        if cat.empty: st.info("Sem categorias.")
        else: st.plotly_chart(plot(px.treemap(cat,path=["Categoria"],values="Valor",title="Mapa de concentração dos gastos")), use_container_width=True)
    st.subheader("💡 Alertas IA")
    alerts=[]
    if ent==0: alerts.append("Cadastre entradas para a IA calcular a situação real do mês.")
    if saldo<0: alerts.append("O mês está negativo. Verifique gastos altos e pendentes.")
    if perc>80: alerts.append("Mais de 80% da renda está comprometida.")
    if pend>0: alerts.append(f"Existem {moeda(pend)} em gastos pendentes.")
    if not alerts: st.success("Nenhum alerta crítico encontrado.")
    for x in alerts: st.warning(x)

elif pagina == "Dashboard":
    st.title("📊 Dashboard Financeiro")
    c1,c2,c3,c4=st.columns(4)
    with c1: fmes=st.selectbox("Mês", ["TODOS"]+MESES)
    with c2: fst=st.selectbox("Status", STATUS)
    with c3: fcat=st.selectbox("Categoria", ["TODAS"]+sorted(gastos["Categoria"].dropna().unique().tolist()))
    with c4: fcar=st.selectbox("Cartão", ["TODOS"]+sorted(gastos["Cartão"].dropna().unique().tolist()))
    df=gastos.copy()
    if fmes!="TODOS": df=df[df["Mês"]==fmes]
    if fst!="TODOS": df=df[df["Status"]==fst]
    if fcat!="TODAS": df=df[df["Categoria"]==fcat]
    if fcar!="TODOS": df=df[df["Cartão"]==fcar]
    total=df.loc[df["Status"]!="CANCELAMENTO","Valor"].sum(); pago=df.loc[df["Status"]=="PAGO","Valor"].sum(); pend=df.loc[df["Status"]=="NÃO","Valor"].sum(); canc=df.loc[df["Status"]=="CANCELAMENTO","Valor"].sum()
    a,b,c,d,e=st.columns(5); a.metric("Total",moeda(total)); b.metric("Pago",moeda(pago)); c.metric("Pendente",moeda(pend)); d.metric("Cancelado",moeda(canc)); e.metric("Lançamentos",len(df))
    base=df[df["Status"]!="CANCELAMENTO"]
    g1,g2=st.columns(2)
    with g1: st.plotly_chart(plot(px.bar(base.groupby("Categoria",as_index=False)["Valor"].sum().sort_values("Valor",ascending=False),x="Categoria",y="Valor",text_auto=".2f",title="Gastos por categoria")), use_container_width=True)
    with g2: st.plotly_chart(plot(px.pie(base.groupby("Cartão",as_index=False)["Valor"].sum(),names="Cartão",values="Valor",hole=.45,title="Gastos por cartão")), use_container_width=True)
    g3,g4=st.columns(2)
    with g3:
        m=base.groupby("Mês",as_index=False)["Valor"].sum(); m["Ordem"]=m["Mês"].apply(lambda x: MESES.index(x) if x in MESES else 99); m=m.sort_values("Ordem")
        st.plotly_chart(plot(px.area(m,x="Mês",y="Valor",markers=True,title="Evolução mensal")), use_container_width=True)
    with g4: st.plotly_chart(plot(px.pie(df.groupby("Status",as_index=False)["Valor"].sum(),names="Status",values="Valor",hole=.55,title="Status dos gastos")), use_container_width=True)
    show=df.copy(); show["Valor"]=show["Valor"].apply(moeda); st.dataframe(show,use_container_width=True,hide_index=True)

elif pagina == "Adicionar Novos Valores":
    st.title("➕ Adicionar Novos Valores")
    with st.form("gasto", clear_on_submit=True):
        a,b=st.columns(2)
        with a:
            data_l=date_input = st.date_input("Data", value=date.today())
            car_sel=st.selectbox("Cartão / Conta", opcoes(excel,app_df,"CARTÃO","Cartão","NÃO INFORMADO")); car=st.text_input("Novo Cartão / Conta") if car_sel=="OUTRO / CADASTRAR NOVO" else car_sel
            des_sel=st.selectbox("Descrição", opcoes(excel,app_df,"DESCRIÇÃO","Descrição","SEM DESCRIÇÃO")); des=st.text_input("Nova Descrição") if des_sel=="OUTRO / CADASTRAR NOVO" else des_sel
            cat_sel=st.selectbox("Categoria", opcoes(excel,app_df,"CATEGORIA","Categoria","SEM CATEGORIA")); cat=st.text_input("Nova Categoria") if cat_sel=="OUTRO / CADASTRAR NOVO" else cat_sel
        with b:
            mes=st.selectbox("Mês",MESES); valor=st.number_input("Valor",min_value=0.0,step=1.0,format="%.2f"); stt=st.selectbox("Status",["NÃO","PAGO","CANCELAMENTO"])
        if st.form_submit_button("Salvar lançamento"):
            if valor<=0 or not str(car).strip() or not str(des).strip() or not str(cat).strip(): st.error("Preencha todos os campos corretamente.")
            else:
                df=ler_gastos_app(); novo={"ID":prox_id(df,"NOVO"),"Origem":"APP","Data":data_l.strftime("%d/%m/%Y"),"Cartão":car,"Descrição":des,"Categoria":cat,"Mês":mes,"Valor":valor,"Status":stt}; salvar(pd.concat([df,pd.DataFrame([novo])],ignore_index=True),ARQ_GASTOS); st.success("Lançamento salvo!"); st.rerun()
    view=ler_gastos_app(); view["Valor"]=pd.to_numeric(view["Valor"],errors="coerce").fillna(0).apply(moeda); st.dataframe(view.tail(30).sort_index(ascending=False),use_container_width=True,hide_index=True)

elif pagina == "Entradas / Receitas":
    st.title("💵 Entradas / Receitas")
    with st.form("entrada", clear_on_submit=True):
        a,b=st.columns(2)
        with a:
            data_e=st.date_input("Data da entrada", value=date.today()); desc=st.text_input("Descrição", placeholder="Salário, renda extra..."); cat=st.selectbox("Categoria",["SALÁRIO","RENDA EXTRA","REEMBOLSO","VALE / BENEFÍCIO","OUTROS","OUTRO / CADASTRAR NOVO"]); cat=st.text_input("Nova categoria") if cat=="OUTRO / CADASTRAR NOVO" else cat
        with b:
            mes=st.selectbox("Mês",MESES); val=st.number_input("Valor",min_value=0.0,step=1.0,format="%.2f")
        if st.form_submit_button("Salvar entrada"):
            if val<=0 or not desc.strip() or not str(cat).strip(): st.error("Preencha todos os campos corretamente.")
            else:
                df=ler_entradas(); nova={"ID":prox_id(df,"ENTRADA"),"Data":data_e.strftime("%d/%m/%Y"),"Descrição":desc,"Categoria":cat,"Mês":mes,"Valor":val}; salvar(pd.concat([df,pd.DataFrame([nova])],ignore_index=True),ARQ_ENTRADAS); st.success("Entrada salva!"); st.rerun()
    df=ler_entradas();
    if not df.empty:
        st.metric("Total de entradas", moeda(df["Valor"].sum())); st.plotly_chart(plot(px.pie(df.groupby("Categoria",as_index=False)["Valor"].sum(),names="Categoria",values="Valor",hole=.45,title="Entradas por categoria")),use_container_width=True); show=df.copy(); show["Valor"]=show["Valor"].apply(moeda); st.dataframe(show,use_container_width=True,hide_index=True)
    else: st.info("Nenhuma entrada cadastrada.")

elif pagina == "Análise Financeira do Mês":
    st.title("📈 Análise Financeira do Mês")
    mes=st.selectbox("Mês",MESES)
    gm=gastos[(gastos["Mês"]==mes)&(gastos["Status"]!="CANCELAMENTO")].copy(); em=entradas[entradas["Mês"]==mes].copy()
    ent=em["Valor"].sum() if not em.empty else 0; sai=gm["Valor"].sum() if not gm.empty else 0; saldo=ent-sai; perc=(sai/ent*100) if ent>0 else 0; cl,rec=saude(perc,saldo)
    a,b,c,d,e=st.columns(5); a.metric("Entradas",moeda(ent)); b.metric("Gastos",moeda(sai)); c.metric("Saldo",moeda(saldo)); d.metric("% comprometido",f"{perc:.1f}%"); e.metric("Situação",cl)
    st.markdown(f'<div class="ia-card"><h3>Resumo inteligente</h3><p>{rec}</p></div>', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1: st.plotly_chart(plot(px.bar(pd.DataFrame({"Tipo":["Entradas","Gastos","Saldo"],"Valor":[ent,sai,saldo]}),x="Tipo",y="Valor",text_auto=".2f",title="Resumo financeiro")),use_container_width=True)
    with c2:
        if ent>0: st.plotly_chart(plot(px.pie(pd.DataFrame({"Tipo":["Gastos","Sobra" if saldo>=0 else "Déficit"],"Valor":[sai,abs(saldo)]}),names="Tipo",values="Valor",hole=.5,title="Distribuição da renda")),use_container_width=True)
    c3,c4=st.columns(2)
    with c3:
        top=gm.sort_values("Valor",ascending=False).head(10); fig=px.bar(top,x="Valor",y="Descrição",color="Categoria",orientation="h",text_auto=".2f",title="Maiores gastos"); fig.update_layout(yaxis={"categoryorder":"total ascending"}); st.plotly_chart(plot(fig),use_container_width=True)
    with c4: st.plotly_chart(plot(px.sunburst(gm.groupby("Categoria",as_index=False)["Valor"].sum(),path=["Categoria"],values="Valor",title="Concentração por categoria")),use_container_width=True)

elif pagina == "Buscar / Atualizar Gastos":
    st.title("🔎 Buscar / Atualizar Gastos")
    busca=st.text_input("Buscar")
    a,b,c,d=st.columns(4)
    with a: fmes=st.selectbox("Mês",["TODOS"]+MESES,key="bm")
    with b: fst=st.selectbox("Status",STATUS,key="bs")
    with c: fcar=st.selectbox("Cartão",["TODOS"]+sorted(gastos["Cartão"].dropna().unique().tolist()),key="bc")
    with d: forg=st.selectbox("Origem",["TODOS","APP","PLANILHA"],key="bo")
    df=gastos.copy()
    if busca.strip(): df=df[df.astype(str).apply(lambda r: r.str.lower().str.contains(busca.strip().lower(),na=False).any(),axis=1)]
    if fmes!="TODOS": df=df[df["Mês"]==fmes]
    if fst!="TODOS": df=df[df["Status"]==fst]
    if fcar!="TODOS": df=df[df["Cartão"]==fcar]
    if forg!="TODOS": df=df[df["Origem"]==forg]
    if df.empty: st.warning("Nenhum gasto encontrado.")
    else:
        def rot(l): return f'{l["ID"]} | {l["Origem"]} | {l["Cartão"]} | {l["Descrição"]} | {l["Mês"]} | {moeda(l["Valor"])} | Atual: {l["Status"]}'
        ops={rot(l):{"ID":l["ID"],"Origem":l["Origem"]} for _,l in df.iterrows()}
        sel=st.selectbox("Gasto encontrado",list(ops.keys())); novo=st.selectbox("Alterar status para",["PAGO","CANCELAMENTO","NÃO"])
        if st.button("Salvar alteração"):
            atualizar_status(ops[sel]["ID"],ops[sel]["Origem"],novo); st.success("Status atualizado!"); st.rerun()
        show=df.copy(); show["Valor"]=show["Valor"].apply(moeda); st.dataframe(show,use_container_width=True,hide_index=True)

elif pagina == "Base de Dados":
    st.title("📁 Base de Dados")
    a1,a2,a3,a4,a5=st.tabs(["Base Consolidada","Lançamentos do App","Entradas","Status Planilha","Planilha Original"])
    with a1:
        show=gastos.copy(); show["Valor"]=show["Valor"].apply(moeda); st.dataframe(show,use_container_width=True,hide_index=True); st.download_button("Baixar CSV",data=gastos.to_csv(index=False).encode("utf-8-sig"),file_name="base_consolidada.csv",mime="text/csv")
    with a2: st.dataframe(ler_gastos_app(),use_container_width=True,hide_index=True)
    with a3: st.dataframe(ler_entradas(),use_container_width=True,hide_index=True)
    with a4: st.dataframe(ler_status(),use_container_width=True,hide_index=True)
    with a5: st.dataframe(excel,use_container_width=True,hide_index=True)
