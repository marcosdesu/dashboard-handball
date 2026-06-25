import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuración visual de la página web
st.set_page_config(page_title="Handball Femenil - Rendimiento", page_icon="🤾‍♀️", layout="wide")

# 1. DICCIONARIO Y FUNCIONES BASE
map_inbody_vald = {
    '<amtm>': 'Angela Madeline Tapia Medina', '<hcrgdlc>': 'Cinthia Raquel Gallegos de la cruz',
    '<hdypc>': 'Dahena Yamileth Paz Corral ', '<heahr>': 'Eva Anahi Hernandez Romero',
    '<hfera>': 'Fernanda Elizabeth Rivera Arreola', '<hiag>': 'Itzel Aguirre Gallegos',
    '<hidldlr>': 'Isabella De Leon de la Rosa', '<hievc>': 'Itzel Esmeralda Vargas Cortes ',
    '<hjalv>': 'Jaqueline Alexandra Lopez Verdugo', '<hkavr>': 'Karewit Alexandra Venancio Ramos',
    '<hlms>': 'Laura Morales Sanchez', '<hnga>': 'Nataly Gonzalez Alameda',
    '<hnjc>': 'Nashely Jaramillo Catañon', '<hphh>': 'Perla Hernandez Hidalgo',
    '<hsspo>': 'Sayra Stephanie Pereira Ortiz'
}

def clean_asym(val):
    if pd.isna(val): return np.nan
    val_str = str(val).strip().upper()
    try:
        num = float(''.join(c for c in val_str if c.isdigit() or c == '.'))
        return -num if 'L' in val_str else num
    except: return np.nan

def limpiar_duplicados_por_hora(df):
    if 'Name' not in df.columns or 'Time' not in df.columns: return df
    df['Time_Parsed'] = pd.to_datetime(df['Time'], format='%I:%M %p', errors='coerce')
    df = df.sort_values(by=['Name', 'Time_Parsed'], ascending=[True, False])
    return df.drop_duplicates(subset=['Name'], keep='first').drop(columns=['Time_Parsed'])

# 2. CARGA DE DATOS
@st.cache_data
def load_data():
    df_squat = limpiar_duplicados_por_hora(pd.read_csv("Squat assessment-05_19_2026.csv"))
    df_ab = limpiar_duplicados_por_hora(pd.read_csv("Abalakov-05_19_2026.csv"))
    df_dj = limpiar_duplicados_por_hora(pd.read_csv("Drop Jump-05_19_2026.csv"))
    df_sldj = limpiar_duplicados_por_hora(pd.read_csv("Single Leg Drop Jump-05_19_2026.csv"))
    df_inbody = pd.read_csv("inbody270_data.csv")
    
    df_inbody['Name'] = df_inbody['1. ID'].map(map_inbody_vald)
    df_inbody = df_inbody.dropna(subset=['Name'])

    df_sq_c = df_squat[['Name', 'Peak Force [N] ', 'Peak Force % (Asym) (%)']].rename(columns={'Peak Force [N] ': 'SQ_Peak_Force_N', 'Peak Force % (Asym) (%)': 'SQ_Asym'})
    df_ab_c = df_ab[['Name', 'Jump Height (Flight Time) [cm] ']].rename(columns={'Jump Height (Flight Time) [cm] ': 'ABA_JumpHeight_cm'})
    df_dj_c = df_dj[['Name', 'RSI (Flight Time/Contact Time) ']].rename(columns={'RSI (Flight Time/Contact Time) ': 'DJ_RSI'})
    df_sldj_c = df_sldj[['Name', 'Peak Landing Force / BW  (Asym)(%)']].rename(columns={'Peak Landing Force / BW  (Asym)(%)': 'SLDJ_Landing_Asym'})
    df_inb_c = df_inbody[['Name', '2. Height', '6. Weight', '24. SMM (Skeletal Muscle Mass)', '30. PBF (Percent Body Fat)']].rename(columns={'2. Height': 'Height_cm', '6. Weight': 'Weight_kg', '24. SMM (Skeletal Muscle Mass)': 'Muscle_Mass_kg', '30. PBF (Percent Body Fat)': 'BodyFat_%'})

    dfs = [df_sq_c, df_ab_c, df_dj_c, df_sldj_c, df_inb_c]
    df_master = dfs[0]
    for d in dfs[1:]: df_master = df_master.merge(d, on='Name', how='outer')

    df_master['SQ_Asym_Num'] = df_master['SQ_Asym'].apply(clean_asym)
    df_master['SLDJ_Landing_Asym_Num'] = df_master['SLDJ_Landing_Asym'].apply(clean_asym)
    return df_master

df_master = load_data()
team_mean = df_master.mean(numeric_only=True)

# --- INTERFAZ WEB ---
st.title("🤾‍♀️ Selección Nacional de Handball Femenil")
st.subheader("Sistema de Monitoreo Físico y Prevención de Lesiones")

tab1, tab2 = st.tabs(["📊 Diagnóstico Individual", "🔥 Mapa de Calor Colectivo"])

with tab1:
    lista_jugadoras = sorted(df_master['Name'].dropna().unique())
    jugadora_sel = st.selectbox("Selecciona una jugadora:", lista_jugadoras)
    
    p_data = df_master[df_master['Name'] == jugadora_sel].iloc[0]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estatura", f"{p_data['Height_cm']:.1f} cm")
    c2.metric("Peso Corporal", f"{p_data['Weight_kg']:.1f} kg")
    c3.metric("Masa Muscular (SMM)", f"{p_data['Muscle_Mass_kg']:.1f} kg")
    c4.metric("Grasa Corporal", f"{p_data['BodyFat_%']:.1f}%")
    
    if pd.isna(p_data['ABA_JumpHeight_cm']):
        st.warning("⚠️ Esta jugadora no realizó las pruebas de salto en esta sesión.")
        
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        asym_at = 0 if pd.isna(p_data['SLDJ_Landing_Asym_Num']) else p_data['SLDJ_Landing_Asym_Num']
        asym_fz = 0 if pd.isna(p_data['SQ_Asym_Num']) else p_data['SQ_Asym_Num']
        
        max_asym = max(abs(asym_at), abs(asym_fz))
        limite_x = max(20.0, float(np.ceil((max_asym + 5.0) / 5.0) * 5.0))
        
        # --- GENERADOR INTUITIVO DE ETIQUETAS ---
        etiquetas_humanas = []
        for v in [asym_at, asym_fz]:
            if v < 0: etiquetas_humanas.append(f"◄ Lado IZQ ({abs(v):.1f}%)")
            elif v > 0: etiquetas_humanas.append(f"Lado DER ({v:.1f}%) ►")
            else: etiquetas_humanas.append("Simétrico (0%)")
        # ----------------------------------------

        fig_asym = go.Figure(go.Bar(
            y=['Asimetría Aterrizaje (1 Pierna)', 'Asimetría Sentadilla (Fuerza)'],
            x=[asym_at, asym_fz], orientation='h',
            marker_color=['red' if abs(x) > 10 else '#2E8B57' for x in [asym_at, asym_fz]],
            text=etiquetas_humanas, textposition='auto'
        ))
        
        fig_asym.update_layout(
            title="Riesgo Biomecánico de LCA (% Asimetría)", 
            xaxis=dict(
                range=[-limite_x, limite_x],
                title="◄  Lado IZQUIERDO   —   0% (Centro)   —   Lado DERECHO  ►"
            ), 
            height=350, template="plotly_white"
        )
        fig_asym.add_vline(x=-10, line_dash="dash", line_color="orange")
        fig_asym.add_vline(x=10, line_dash="dash", line_color="orange")
        st.plotly_chart(fig_asym, use_container_width=True)

    with col_der:
        mets = ['SQ_Peak_Force_N', 'ABA_JumpHeight_cm', 'DJ_RSI', 'Muscle_Mass_kg']
        lbls = ['Fuerza Máx.', 'Salto Abalakov', 'Reactividad RSI', 'Masa Muscular']
        p_pct = [0 if pd.isna(p_data[m]) else (p_data[m]/team_mean[m])*100 for m in mets]
        t_pct = [100, 100, 100, 100]
        
        techo = max(150.0, float(np.ceil((max(p_pct)+15)/10)*10))
        suelo = max(0.0, min(50.0, float(np.floor(min(p_pct)/10)*10)))
        
        fig_rad = go.Figure()
        fig_rad.add_trace(go.Scatterpolar(r=t_pct+[100], theta=lbls+[lbls[0]], fill='toself', name='Promedio Equipo', line_color='gray', opacity=0.4))
        fig_rad.add_trace(go.Scatterpolar(r=p_pct+[p_pct[0]], theta=lbls+[lbls[0]], fill='toself', name=jugadora_sel, line_color='#1E90FF'))
        fig_rad.update_layout(title="Rendimiento vs Media del Equipo (100%)", polar=dict(radialaxis=dict(visible=True, range=[suelo, techo])), height=400, template="plotly_white")
        st.plotly_chart(fig_rad, use_container_width=True)

with tab2:
    st.markdown("### Matriz Táctica de Plantilla")
    st.caption("Valores expresados en % respecto a la media del equipo. Rojo: <80% | Amarillo: 80-99% | Verde: 100%+")
    
    df_heat = df_master[['Name', 'SQ_Peak_Force_N', 'ABA_JumpHeight_cm', 'DJ_RSI', 'Muscle_Mass_kg']].copy()
    for m in ['SQ_Peak_Force_N', 'ABA_JumpHeight_cm', 'DJ_RSI', 'Muscle_Mass_kg']:
        df_heat[m] = (df_heat[m] / team_mean[m]) * 100
    df_heat.columns = ['Jugadora', 'Fuerza Sentadilla', 'Salto Abalakov', 'Reactividad RSI', 'Masa Muscular']
    df_heat.set_index('Jugadora', inplace=True)

    def semaforo_web(val):
        if pd.isna(val): return 'background-color: #EEEEEE; color: #999999;'
        v = round(val, 1)
        if v < 80.0:
            gb = int(40 + (160 * max(0, min(1, (v-50)/30))))
            return f'background-color: rgb(255, {gb}, {gb}); color: black;'
        elif v < 100.0:
            norm = (v - 80.0) / 20.0
            return f'background-color: rgb(255, {int(195+(60*norm))}, {int(210*norm)}); color: black;'
        else:
            norm = min(1.0, (v - 100.0) / 25.0)
            rb = int(190 - (160 * norm))
            return f'background-color: rgb({rb}, {int(240-(90*norm))}, {rb}); color: {"white" if norm > 0.55 else "black"};'

    st.dataframe(df_heat.style.map(semaforo_web).format("{:.1f}%", na_rep="-"), use_container_width=True, height=550)
