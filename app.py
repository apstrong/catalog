import streamlit as st
import yaml
from api_client import OmniAPIClient
import graphviz
from typing import Dict, Any

def create_join_graph(yaml_data: Dict[str, Any], base_table: str) -> graphviz.Digraph:
    """Create a Graphviz diagram showing join relationships from a topic YAML."""
    # Create a new directed graph
    dot = graphviz.Digraph(
        graph_attr={
            'rankdir': 'LR',  # Left to right layout
            'splines': 'ortho',  # Orthogonal lines
            'nodesep': '0.5',  # Node separation
            'ranksep': '1',  # Rank separation
            'fontname': 'Helvetica',
            'bgcolor': 'white',
            'concentrate': 'true'  # Reduce number of edge crossings
        },
        node_attr={
            'fontname': 'Helvetica',
            'fontsize': '11',
            'shape': 'rectangle',
            'style': 'rounded,filled',
            'margin': '0.2',
            'penwidth': '0'  # Remove borders
        },
        edge_attr={
            'fontname': 'Helvetica',
            'fontsize': '10',
            'color': '#666666',
            'arrowsize': '0.8'
        }
    )
    
    # Add base table with special styling
    dot.node(
        base_table,
        base_table,
        fillcolor='#4287f5',  # Blue
        fontcolor='white'
    )
    
    def add_joins(parent_table: str, joins_data: Dict[str, Any], depth: int = 0):
        if not isinstance(joins_data, dict):
            return
            
        for table, join_info in joins_data.items():
            # Color gets lighter as depth increases
            colors = ['#6ba2f7', '#94bdf9', '#bcd8fb', '#e4f1fd']
            fillcolor = colors[min(depth, len(colors)-1)]
            
            # Add the joined table
            dot.node(
                table,
                table,
                fillcolor=fillcolor,
                fontcolor='black' if depth > 0 else 'white'
            )
            
            # Add edge with arrow
            dot.edge(
                parent_table,
                table,
                dir='forward',
                penwidth='1.2',
                arrowhead='vee'
            )
            
            # Recursively process nested joins
            if isinstance(join_info, dict):
                add_joins(table, join_info, depth + 1)
    
    # Process joins if they exist
    if 'joins' in yaml_data:
        add_joins(base_table, yaml_data['joins'])
    
    return dot

def display_file_content(selected_file: str, file_content: str):
    """Helper function to display file content with appropriate formatting."""
    
    # For .topic files, show YAML and join tree side by side
    if selected_file.endswith('.topic'):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("YAML View")
            st.code(file_content, language="yaml")
            
        with col2:
            st.subheader("Join Tree")
            try:
                topic_data = yaml.safe_load(file_content)
                if isinstance(topic_data, dict) and 'joins' in topic_data:
                    # Get base table name from file name (remove .topic extension)
                    base_table = selected_file.replace('.topic', '')
                    
                    # Create and display graph
                    graph = create_join_graph(topic_data, base_table)
                    st.graphviz_chart(graph)
                else:
                    st.info("No join relationships found in this file")
            except Exception as e:
                st.error(f"Error creating join tree: {str(e)}")
    else:
        # For non-topic files, just show YAML
        st.code(file_content, language="yaml")

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
                                
                                # Categorize files
                                topics = [f for f in file_names if f.endswith('.topic')]
                                views = [f for f in file_names if f.endswith('.view')]
                                model_file = next((f for f in file_names if f == "model"), None)
                                relationship_file = next((f for f in file_names if 'relationship' in f.lower()), None)
                                
                                # Create tabs for different file types
                                tab1, tab2, tab3, tab4 = st.tabs(["Model", "Relationships", "Topics", "Views"])
                                
                                with tab1:
                                    if model_file:
                                        display_file_content(model_file, yaml_data["files"][model_file])
                                    else:
                                        st.info("No model file found")
                                        
                                with tab2:
                                    if relationship_file:
                                        display_file_content(relationship_file, yaml_data["files"][relationship_file])
                                    else:
                                        st.info("No relationship file found")
                                        
                                with tab3:
                                    if topics:
                                        selected_topic = st.selectbox(
                                            "Select a topic file",
                                            topics,
                                            index=None,
                                            placeholder="Choose a file..."
                                        )
                                        if selected_topic:
                                            display_file_content(selected_topic, yaml_data["files"][selected_topic])
                                    else:
                                        st.info("No topic files found")
                                        
                                with tab4:
                                    if views:
                                        selected_view = st.selectbox(
                                            "Select a view file",
                                            views,
                                            index=None,
                                            placeholder="Choose a file..."
                                        )
                                        if selected_view:
                                            display_file_content(selected_view, yaml_data["files"][selected_view])
                                    else:
                                        st.info("No view files found")
                            else:
                                st.info("No files found in the model YAML")
                        else:
                            st.error("Unexpected YAML structure")
                    except yaml.YAMLError as e:
                        st.error(f"Error parsing YAML: {str(e)}")
                else:
                    st.error("Failed to fetch model YAML") 