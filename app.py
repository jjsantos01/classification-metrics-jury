import streamlit as st
import sqlite3
import requests
import pandas as pd
import re
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from datetime import datetime
import os
import io

# Page configuration
st.set_page_config(
    page_title="Interactive Judgment App",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Database connection
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('votes.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        case_id INTEGER,
        verdict TEXT,
        ts TIMESTAMP,
        UNIQUE(username, case_id)
    )
    ''')
    conn.commit()
    return conn

# Load cases data
@st.cache_data(ttl=3600)
def load_cases():
    try:
        cases_url = st.secrets.get("CASES_URL", "https://example.com/cases.json")
        response = requests.get(cases_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error loading cases: {str(e)}")
        return []

# Database operations
def get_user_votes(username: str) -> set:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT case_id FROM votes WHERE username = ?", (username,))
    return set(row[0] for row in c.fetchall())

def save_vote(username: str, case_id: int, verdict: str) -> bool:
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO votes (username, case_id, verdict, ts) VALUES (?, ?, ?, ?)",
            (username, case_id, verdict, datetime.now())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Ya votó en este caso
        return False
    except Exception as e:
        st.error(f"Error saving vote: {str(e)}")
        return False

def get_all_votes() -> pd.DataFrame:
    conn = get_db_connection()
    query = "SELECT username, case_id, verdict, ts FROM votes"
    return pd.read_sql_query(query, conn)

def reset_all_votes():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM votes")
    conn.commit()

# Metrics calculation
def confusion_components(df: pd.DataFrame, threshold: float = 0.5):
    if df.empty:
        return {
            'case_metrics': pd.DataFrame(),
            'accuracy': 0,
            'precision': 0,
            'recall': 0,
            'f1': 0
        }
        
    case_metrics = df.groupby('case_id').agg(
        total_votes=('verdict', 'count'),
        guilty_votes=('verdict', lambda x: (x == 'guilty').sum())
    )
    
    case_metrics['p_guilty'] = case_metrics['guilty_votes'] / case_metrics['total_votes']
    case_metrics['prediction'] = (case_metrics['p_guilty'] > threshold).map({True: 'guilty', False: 'innocent'})
    
    cases = load_cases()
    case_ground_truth = {case['id']: case['ground_truth'] for case in cases}
    
    case_metrics['ground_truth'] = case_metrics.index.map(lambda x: case_ground_truth.get(x))
    case_metrics['correct'] = case_metrics['prediction'] == case_metrics['ground_truth']
    
    y_true = case_metrics['ground_truth'].map({'guilty': 1, 'innocent': 0}).values
    y_pred = case_metrics['prediction'].map({'guilty': 1, 'innocent': 0}).values
    
    try:
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
    except:
        accuracy = precision = recall = f1 = 0
    
    return {
        'case_metrics': case_metrics,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

# UI Components
def render_login_view():
    # Display header
    st.title("⚖️ Interactive Judgment App")
    st.markdown("### Bienvenido! Ingresa tu nombre de usuario para comenzar")
    
    # Get username from query params if available
    default_username = st.query_params.get("username", "")
    default_password = st.query_params.get("admin_pwd", "") if default_username.lower() == "admin" else ""
    
    with st.form("login_form"):
        username = st.text_input(
            "Nombre de usuario (3-20 caracteres alfanuméricos, guión o underscore)",
            value=default_username
        )
        
        if username.lower() == "admin":
            password = st.text_input(
                "Contraseña de Administrador", 
                type="password",
                value=default_password
            )
        else:
            password = None
            
        submit_button = st.form_submit_button("Comenzar")
        
        if submit_button:
            if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', username):
                st.error("El nombre de usuario debe tener 3-20 caracteres alfanuméricos, guión o underscore")
                return
                
            if username.lower() == "admin":
                admin_pwd = os.environ.get("ADMIN_PWD", st.secrets.get("ADMIN_PWD", ""))
                if password != admin_pwd:
                    st.error("Contraseña de administrador incorrecta")
                    return
                st.session_state["admin_logged"] = True
                st.query_params["admin_pwd"] = password
            
            # Actualizar estado de sesión y query params
            st.session_state["username"] = username
            st.session_state["current_case"] = 0
            st.session_state["voted_cases"] = get_user_votes(username)
            
            # Guardar en query params para persistencia
            st.query_params["username"] = username
            
            st.rerun()

def render_case_view(cases):
    if not cases:
        st.title("⚖️ Interactive Judgment App")
        st.error("No hay casos disponibles. Intenta más tarde.")
        return
        
    username = st.session_state["username"]
    current_case_idx = st.session_state["current_case"]
    voted_cases = st.session_state["voted_cases"]
    
    st.title("⚖️ Interactive Judgment App")
    st.markdown(f"**Usuario:** {username}")
    
    total_cases = len(cases)
    voted_count = len(voted_cases)
    
    # Barra de progreso
    st.progress(voted_count / total_cases)
    st.markdown(f"**Progreso:** {voted_count}/{total_cases} casos juzgados")
    
    if current_case_idx < total_cases:
        case = cases[current_case_idx]
        case_id = case["id"]
        
        st.markdown(f"### Caso #{case_id}")
        
        if "image" in case and case["image"]:
            st.image(case["image"], caption=f"Acusado - Caso #{case_id}")
        
        st.markdown(f"**Descripción:**\n{case['description']}")
        
        already_voted = case_id in voted_cases
        
        # Botones de votación
        col1, col2 = st.columns(2)
        with col1:
            guilty_button = st.button(
                "CULPABLE 🔴", 
                disabled=already_voted,
                use_container_width=True,
                type="primary" if not already_voted else "secondary"
            )
            
        with col2:
            innocent_button = st.button(
                "INOCENTE 🟢", 
                disabled=already_voted,
                use_container_width=True,
                type="primary" if not already_voted else "secondary"
            )
            
        if already_voted:
            st.info("Ya has votado en este caso")
            
        # Procesar voto
        if guilty_button:
            if save_vote(username, case_id, "guilty"):
                st.session_state["voted_cases"].add(case_id)
                st.success("Voto registrado: CULPABLE")
                st.rerun()
            
        if innocent_button:
            if save_vote(username, case_id, "innocent"):
                st.session_state["voted_cases"].add(case_id)
                st.success("Voto registrado: INOCENTE")
                st.rerun()
        
        # Navegación entre casos
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            prev_button = st.button(
                "◀️ Anterior", 
                disabled=current_case_idx == 0,
                use_container_width=True
            )
            
        with col2:
            next_button = st.button(
                "Siguiente ▶️", 
                disabled=current_case_idx == total_cases - 1,
                use_container_width=True
            )
            
        if prev_button and current_case_idx > 0:
            st.session_state["current_case"] -= 1
            st.query_params["case"] = st.session_state["current_case"]
            st.rerun()
            
        if next_button and current_case_idx < total_cases - 1:
            st.session_state["current_case"] += 1
            st.query_params["case"] = st.session_state["current_case"]
            st.rerun()
    
    if voted_count == total_cases:
        st.success("🎉 ¡Gracias por votar en todos los casos! Espera a que el instructor comparta los resultados.")

def render_admin_view(cases):
    st.title("⚖️ Panel de Administración")
    
    votes_df = get_all_votes()
    
    if votes_df.empty:
        st.warning("No hay votos registrados aún")
        return
    
    # Mostrar resultados por caso primero
    st.markdown("## Resultados de Votación por Caso")
    
    # Configuración del umbral en la parte superior
    threshold = st.slider(
        "Umbral para veredicto de Culpable", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.5,
        step=0.05
    )
    
    # Calcular métricas
    results = confusion_components(votes_df, threshold)
    case_metrics = results['case_metrics']
    
    case_dict = {case['id']: case for case in cases}
    
    for case_id, metrics in case_metrics.iterrows():
        if case_id not in case_dict:
            continue
            
        case = case_dict[case_id]
        
        with st.expander(f"Caso #{case_id} - {metrics['correct'] and '✅ Correcto' or '❌ Incorrecto'}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if "image" in case and case["image"]:
                    st.image(case["image"], caption=f"Acusado - Caso #{case_id}")
            
            with col2:
                st.markdown(f"**Descripción:** {case['description']}")
                st.markdown(f"**Verdad:** {case['ground_truth'].upper()}")
                st.markdown(f"**Veredicto del Jurado:** {metrics['prediction'].upper()} (p={metrics['p_guilty']:.2f})")
                
                st.markdown(f"**Total de Votos:** {metrics['total_votes']}")
                st.markdown(f"**Votos Culpable:** {metrics['guilty_votes']}")
                st.markdown(f"**Votos Inocente:** {metrics['total_votes'] - metrics['guilty_votes']}")
                
                st.bar_chart({
                    'Culpable': [metrics['guilty_votes']],
                    'Inocente': [metrics['total_votes'] - metrics['guilty_votes']]
                })
    
    # Ahora mostramos las métricas globales y herramientas debajo
    st.markdown("---")
    st.markdown("## Panel de Control")
    
    # Mostrar métricas globales
    st.markdown("### Métricas Globales")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accuracy", f"{results['accuracy']:.2f}")
    col2.metric("Precision", f"{results['precision']:.2f}")
    col3.metric("Recall", f"{results['recall']:.2f}")
    col4.metric("F1 Score", f"{results['f1']:.2f}")
    
    # Opciones de administración
    st.markdown("### Herramientas de Administración")
    if st.button("Descargar votes.db"):
        with open('votes.db', 'rb') as f:
            bytes_data = f.read()
        st.download_button(
            label="Descargar archivo votes.db",
            data=bytes_data,
            file_name="votes.db",
            mime="application/octet-stream"
        )
    
    # Manejo del reset de votos con estados
    st.markdown("### Zona de Peligro")
    
    # Inicializar estado para el proceso de reset
    if "reset_step" not in st.session_state:
        st.session_state["reset_step"] = 0
    
    # Paso 1: Mostrar botón inicial
    if st.session_state["reset_step"] == 0:
        if st.button("Reiniciar Todos los Votos"):
            st.session_state["reset_step"] = 1
            st.rerun()
    
    # Paso 2: Mostrar checkbox de confirmación
    elif st.session_state["reset_step"] == 1:
        st.warning("¡Esta acción eliminará todos los votos!")
        confirm = st.checkbox("Confirmo que quiero eliminar TODOS los votos")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancelar"):
                st.session_state["reset_step"] = 0
                st.rerun()
        
        with col2:
            if st.button("SÍ, eliminar todo", type="primary", disabled=not confirm):
                if confirm:
                    reset_all_votes()
                    st.session_state["reset_step"] = 0
                    st.success("Todos los votos han sido reiniciados")
                    st.rerun()

def main():
    # Inicializar estado de sesión
    if "username" not in st.session_state:
        # Intentar recuperar de query params
        if "username" in st.query_params:
            username = st.query_params["username"]
            st.session_state["username"] = username
            st.session_state["voted_cases"] = get_user_votes(username)
            
            # Verificar admin
            if username.lower() == "admin" and "admin_pwd" in st.query_params:
                admin_pwd = os.environ.get("ADMIN_PWD", st.secrets.get("ADMIN_PWD", ""))
                if st.query_params["admin_pwd"] == admin_pwd:
                    st.session_state["admin_logged"] = True
        else:
            st.session_state["username"] = None
    
    if "current_case" not in st.session_state:
        # Recuperar índice de caso actual
        if "case" in st.query_params:
            try:
                st.session_state["current_case"] = int(st.query_params["case"])
            except ValueError:
                st.session_state["current_case"] = 0
        else:
            st.session_state["current_case"] = 0
    
    if "voted_cases" not in st.session_state:
        st.session_state["voted_cases"] = set()
    
    if "admin_logged" not in st.session_state:
        st.session_state["admin_logged"] = False
    
    # Cargar casos
    cases = load_cases()
    
    # Renderizar vista apropiada
    if not st.session_state["username"]:
        render_login_view()
    else:
        # Botón de cerrar sesión en la parte superior
        if st.button("Cerrar Sesión", key="logout_button"):
            st.session_state["username"] = None
            st.session_state["current_case"] = 0
            st.session_state["voted_cases"] = set()
            st.session_state["admin_logged"] = False
            st.query_params.clear()
            st.rerun()
            
        if st.session_state["admin_logged"]:
            render_admin_view(cases)
        else:
            render_case_view(cases)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "Creado para Bootcamp de Data Science | "
        "[GitHub Repo](https://github.com/yourusername/interactive-judgment-app)"
    )

if __name__ == "__main__":
    main()