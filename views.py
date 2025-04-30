import streamlit as st
import re
import os
from datetime import datetime

# Importar funciones de utilidad
from utils import (
    get_db_connection, load_cases, get_user_votes, get_user_verdict, 
    save_vote, update_vote, get_all_votes, reset_all_votes,
    get_config, set_config, get_show_results_to_students, set_show_results_to_students,
    confusion_components, get_confusion_matrix_html
)

def render_login_view():
    """Renderiza la vista de inicio de sesión"""
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
                admin_pwd = os.environ["ADMIN_PWD"]
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
    """Renderiza la vista para votar en casos"""
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
        current_verdict = None
        
        # Obtener el veredicto actual si ya votó
        if already_voted:
            current_verdict = get_user_verdict(username, case_id)
            st.info(f"Tu veredicto actual: **{current_verdict.upper()}**. Puedes cambiar tu decisión si lo deseas.")
        
        # Botones de votación (se resaltan según el veredicto actual)
        col1, col2 = st.columns(2)
        with col1:
            guilty_button = st.button(
                "CULPABLE 🔴", 
                use_container_width=True,
                type="primary" if current_verdict == "guilty" else "secondary"
            )
            
        with col2:
            innocent_button = st.button(
                "INOCENTE 🟢", 
                use_container_width=True,
                type="primary" if current_verdict == "innocent" else "secondary"
            )
            
        # Procesar voto nuevo o actualización
        if guilty_button:
            if already_voted:
                if current_verdict != "guilty":
                    if update_vote(username, case_id, "guilty"):
                        st.success("Voto actualizado: CULPABLE")
                        st.rerun()
                    else:
                        st.error("No se pudo actualizar el voto")
            else:
                if save_vote(username, case_id, "guilty"):
                    st.session_state["voted_cases"].add(case_id)
                    st.success("Voto registrado: CULPABLE")
                    st.rerun()
            
        if innocent_button:
            if already_voted:
                if current_verdict != "innocent":
                    if update_vote(username, case_id, "innocent"):
                        st.success("Voto actualizado: INOCENTE")
                        st.rerun()
                    else:
                        st.error("No se pudo actualizar el voto")
            else:
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

def render_results_view(cases, threshold=0.5):
    """Renderiza la vista de resultados para estudiantes"""
    st.title("⚖️ Resultados del Juicio Interactivo")
    username = st.session_state["username"]
    st.markdown(f"**Usuario:** {username}")
    
    votes_df = get_all_votes()
    
    if votes_df.empty:
        st.warning("No hay votos registrados aún.")
        return
    
    # Calcular métricas con el umbral predeterminado
    results = confusion_components(votes_df, threshold)
    case_metrics = results['case_metrics']
    
    # Mostrar métricas globales
    st.markdown("## Métricas Globales")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accuracy", f"{results['accuracy']:.2f}")
    col2.metric("Precision", f"{results['precision']:.2f}")
    col3.metric("Recall", f"{results['recall']:.2f}")
    col4.metric("F1 Score", f"{results['f1']:.2f}")
    
    # Matriz de confusión
    st.markdown("## Matriz de Confusión")
    
    # Calcular los valores de la matriz
    y_true = case_metrics['ground_truth'].map({'guilty': 1, 'innocent': 0}).values
    y_pred = case_metrics['prediction'].map({'guilty': 1, 'innocent': 0}).values
    
    # Calcular componentes de la matriz de confusión
    TP = sum((y_true == 1) & (y_pred == 1))
    FP = sum((y_true == 0) & (y_pred == 1))
    FN = sum((y_true == 1) & (y_pred == 0))
    TN = sum((y_true == 0) & (y_pred == 0))
    
    # Obtener y mostrar la matriz de confusión
    matrix_html = get_confusion_matrix_html(TN, FP, FN, TP)
    st.markdown(matrix_html, unsafe_allow_html=True)
    
    # Mostrar resultados por caso
    st.markdown("## Resultados de Votación por Caso")
    
    case_dict = {case['id']: case for case in cases}
    
    for case_id, metrics in case_metrics.iterrows():
        if case_id not in case_dict:
            continue
            
        case = case_dict[case_id]
        
        # Verificar si el usuario votó en este caso
        user_vote = None
        user_votes = votes_df[votes_df['username'] == username]
        if not user_votes.empty:
            case_vote = user_votes[user_votes['case_id'] == case_id]
            if not case_vote.empty:
                user_vote = case_vote['verdict'].iloc[0]
        
        with st.expander(f"Caso #{case_id} - {metrics['correct'] and '✅ Correcto' or '❌ Incorrecto'}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if "image" in case and case["image"]:
                    st.image(case["image"], caption=f"Acusado - Caso #{case_id}")
            
            with col2:
                st.markdown(f"**Descripción:** {case['description']}")
                st.markdown(f"**Verdad:** {case['ground_truth'].upper()}")
                st.markdown(f"**Veredicto del Jurado:** {metrics['prediction'].upper()} (p={metrics['p_guilty']:.2f})")
                
                if user_vote:
                    verdict_color = "green" if user_vote == case['ground_truth'] else "red"
                    st.markdown(f"**Tu voto:** <span style='color:{verdict_color}'>{user_vote.upper()}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Total de Votos:** {metrics['total_votes']}")
                st.markdown(f"**Votos Culpable:** {metrics['guilty_votes']}")
                st.markdown(f"**Votos Inocente:** {metrics['total_votes'] - metrics['guilty_votes']}")
                
                st.bar_chart({
                    'Culpable': [metrics['guilty_votes']],
                    'Inocente': [metrics['total_votes'] - metrics['guilty_votes']]
                })

def render_admin_view(cases):
    """Renderiza la vista de administración"""
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
    
    # Opción para permitir a los estudiantes ver los resultados
    current_show_results = get_show_results_to_students()
    show_results = st.checkbox(
        "Permitir a los estudiantes ver los resultados", 
        value=current_show_results
    )
    
    # Actualizar la configuración si cambió
    if show_results != current_show_results:
        if set_show_results_to_students(show_results):
            if show_results:
                st.success("Los estudiantes ahora pueden ver los resultados.")
            else:
                st.success("Los resultados ya no son visibles para los estudiantes.")
        else:
            st.error("No se pudo actualizar la configuración.")
    
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
    
    # Matriz de confusión
    st.markdown("### Matriz de Confusión")
    
    # Calcular los valores de la matriz
    y_true = case_metrics['ground_truth'].map({'guilty': 1, 'innocent': 0}).values
    y_pred = case_metrics['prediction'].map({'guilty': 1, 'innocent': 0}).values
    
    # Calcular componentes de la matriz de confusión
    TP = sum((y_true == 1) & (y_pred == 1))
    FP = sum((y_true == 0) & (y_pred == 1))
    FN = sum((y_true == 1) & (y_pred == 0))
    TN = sum((y_true == 0) & (y_pred == 0))
    
    # Obtener y mostrar la matriz de confusión
    matrix_html = get_confusion_matrix_html(TN, FP, FN, TP)
    st.markdown(matrix_html, unsafe_allow_html=True)
    
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