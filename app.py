import streamlit as st
import yaml
from api_client import OmniAPIClient

st.set_page_config(
    page_title="Omni Catalog",
    page_icon="📚",
    layout="wide"
)

# Initialize API client
try:
    api_client = OmniAPIClient()
except ValueError as e:
    st.error(str(e))
    st.stop()

st.title("📚 Omni Catalog")

# Initialize session state for models data
if 'models_data' not in st.session_state:
    st.session_state.models_data = None

# Fetch models automatically when the app loads
if st.session_state.models_data is None:
    with st.spinner("Loading models..."):
        models_data = api_client.get_models()
        if models_data:
            st.session_state.models_data = models_data
        else:
            st.error("Failed to fetch models")

# If we have models data, show the selector
if st.session_state.models_data and "records" in st.session_state.models_data:
    models = st.session_state.models_data["records"]
    model_names = [model.get("name", "Unnamed Model") for model in models]
    
    selected_model_name = st.selectbox(
        "Select a model",
        model_names,
        index=None,
        placeholder="Choose a model..."
    )
    
    if selected_model_name:
        # Find the selected model's ID
        selected_model = next(
            (model for model in models if model.get("name") == selected_model_name),
            None
        )
        if selected_model:
            model_id = selected_model['id']
            
            # Fetch and display YAML
            with st.spinner("Loading model YAML..."):
                yaml_content = api_client.get_model_yaml(model_id)
                if yaml_content:
                    try:
                        yaml_data = yaml.safe_load(yaml_content)
                        if isinstance(yaml_data, dict) and "files" in yaml_data:
                            file_names = list(yaml_data["files"].keys())
                            if file_names:
                                st.subheader("Files in Model:")
                                selected_file = st.selectbox(
                                    "Select a file to view",
                                    file_names,
                                    index=None,
                                    placeholder="Choose a file..."
                                )
                                
                                if selected_file:
                                    file_content = yaml_data["files"][selected_file]
                                    st.subheader(f"Contents of {selected_file}:")
                                    st.code(file_content, language="yaml")
                            else:
                                st.info("No files found in the model YAML")
                        else:
                            st.error("Unexpected YAML structure")
                    except yaml.YAMLError as e:
                        st.error(f"Error parsing YAML: {str(e)}")
                else:
                    st.error("Failed to fetch model YAML") 