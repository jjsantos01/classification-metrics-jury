import streamlit as st
import os

# Importar todas las funciones necesarias de los módulos refactorizados
from utils import load_cases, get_show_results_to_students, get_user_votes
from views import render_login_view, render_case_view, render_admin_view, render_results_view

# Page configuration
st.set_page_config(
    page_title="Juicio Interactivo",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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
                admin_pwd = os.environ["ADMIN_PWD"]
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
        
        # Determinar qué vista mostrar
        if st.session_state["admin_logged"]:
            # El administrador siempre ve el panel de administración
            render_admin_view(cases)
        elif get_show_results_to_students():
            # Los estudiantes ven los resultados si el admin lo ha habilitado
            render_results_view(cases)
        else:
            # Si no, los estudiantes ven la vista para votar
            render_case_view(cases)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "Creado por [@jjsantoso](https://twitter.com/jjsantoso) | "
        "[GitHub Repo](https://github.com/jjsantos01/classification-metrics-jury)"
    )

if __name__ == "__main__":
    main()