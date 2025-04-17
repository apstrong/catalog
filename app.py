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

def get_fields_from_view(view_data: dict, source_table: str) -> list:
    """Helper function to extract fields from a view file."""
    fields = []
    
    # Process dimensions
    if 'dimensions' in view_data:
        for field_name, field_def in view_data['dimensions'].items():
            fields.append({
                'name': field_name,
                'type': 'Dimension',
                'sql': field_def.get('sql', ''),
                'description': field_def.get('description', ''),
                'source_table': source_table,
                'full_definition': yaml.dump({field_name: field_def}, default_flow_style=False)
            })
    
    # Process measures
    if 'measures' in view_data:
        for field_name, field_def in view_data['measures'].items():
            sql = field_def.get('sql', '')
            agg_type = field_def.get('aggregate_type', '')
            
            # Format SQL display
            if agg_type:
                if sql:
                    sql = f"{agg_type}({sql})"
                else:
                    sql = agg_type
            
            fields.append({
                'name': field_name,
                'type': 'Measure',
                'sql': sql,
                'description': field_def.get('description', ''),
                'source_table': source_table,
                'full_definition': yaml.dump({field_name: field_def}, default_flow_style=False)
            })
    
    return fields

def get_view_file_paths(table_name: str, view_data: dict = None) -> list:
    """Helper function to generate possible view file paths based on schema presence and query parameter."""
    # Check if this is a query view
    is_query = view_data and 'query' in view_data
    view_suffix = '.query.view' if is_query else '.view'
    
    if view_data and 'schema' in view_data:
        # If schema is present, try schema/table_name path
        paths = [
            f"{view_data['schema']}/{table_name}{view_suffix}",
            f"{table_name}{view_suffix}"  # Fallback to just table_name
        ]
    else:
        # If no schema, try both with PUBLIC schema and without
        paths = [f"PUBLIC/{table_name}{view_suffix}", f"{table_name}{view_suffix}"]
        # Also try with .query.view if we don't know for sure
        if not view_data:
            paths.extend([f"PUBLIC/{table_name}.query.view", f"{table_name}.query.view"])
    
    return paths

def collect_all_fields(yaml_data: dict, base_table: str, all_files: dict) -> list:
    """Recursively collect fields from all tables in the join path."""
    all_fields = []
    
    # For base table, first try to load the view to check for query parameter
    basic_paths = [f"{base_table}.view", f"PUBLIC/{base_table}.view", 
                  f"{base_table}.query.view", f"PUBLIC/{base_table}.query.view"]
    base_view_file = next((v for v in basic_paths if v in all_files), None)
    
    if base_view_file:
        try:
            base_view_data = yaml.safe_load(all_files[base_view_file])
            if isinstance(base_view_data, dict):
                # Now get the proper paths based on the view data
                base_view_paths = get_view_file_paths(base_table, base_view_data)
                base_view_file = next((v for v in base_view_paths if v in all_files), None)
                
                base_fields = get_fields_from_view(base_view_data, base_table)
                all_fields.extend(base_fields)
        except Exception as e:
            print(f"Error processing base view {base_view_file}: {str(e)}")
    
    def process_joins(joins_data: dict):
        if not isinstance(joins_data, dict):
            return
            
        for table, join_info in joins_data.items():
            # First try to load the view to check for query parameter
            basic_paths = [f"{table}.view", f"PUBLIC/{table}.view",
                         f"{table}.query.view", f"PUBLIC/{table}.query.view"]
            table_view_file = next((v for v in basic_paths if v in all_files), None)
            
            if table_view_file:
                try:
                    view_data = yaml.safe_load(all_files[table_view_file])
                    if isinstance(view_data, dict):
                        # Get the proper paths based on the view data
                        table_view_paths = get_view_file_paths(table, view_data)
                        table_view_file = next((v for v in table_view_paths if v in all_files), None)
                        
                        table_fields = get_fields_from_view(view_data, table)
                        all_fields.extend(table_fields)
                except Exception as e:
                    print(f"Error processing view {table_view_file}: {str(e)}")
            
            # Process nested joins
            if isinstance(join_info, dict):
                process_joins(join_info)
    
    # Process all joins
    if 'joins' in yaml_data:
        process_joins(yaml_data['joins'])
    
    return all_fields

def display_file_content(selected_file: str, file_content: str, all_files: dict = None):
    """Helper function to display file content with appropriate formatting."""
    
    # For .topic files, show YAML, join tree, and fields table
    if selected_file.endswith('.topic'):
        try:
            topic_data = yaml.safe_load(file_content)
            # Get base table name from base_view parameter if available, otherwise from file name
            if isinstance(topic_data, dict) and 'base_view' in topic_data:
                base_table = topic_data['base_view']
            else:
                base_table = selected_file.replace('.topic', '')
        except Exception:
            base_table = selected_file.replace('.topic', '')
        
        # First row: YAML and Join Tree side by side
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("YAML View")
            st.code(file_content, language="yaml")
            
        with col2:
            st.subheader("Join Tree")
            try:
                topic_data = yaml.safe_load(file_content)
                if isinstance(topic_data, dict) and 'joins' in topic_data:
                    # Create and display graph
                    graph = create_join_graph(topic_data, base_table)
                    st.graphviz_chart(graph)
                else:
                    st.info("No join relationships found in this file")
            except Exception as e:
                st.error(f"Error creating join tree: {str(e)}")
        
        # Second row: Fields table (full width)
        try:
            topic_data = yaml.safe_load(file_content)
            if isinstance(topic_data, dict):
                if all_files:
                    all_fields = collect_all_fields(topic_data, base_table, all_files)
                    if all_fields:
                        # Create DataFrame for the table
                        import pandas as pd
                        df = pd.DataFrame(all_fields)
                        
                        # Add filters
                        col1, col2 = st.columns(2)
                        with col1:
                            selected_tables = st.multiselect(
                                "Filter by Source Table",
                                options=sorted(df['source_table'].unique()),
                                placeholder="Select tables...",
                                key=f"table_filter_{selected_file}"
                            )
                        
                        with col2:
                            selected_types = st.multiselect(
                                "Filter by Type",
                                options=sorted(df['type'].unique()),
                                placeholder="Select types...",
                                key=f"type_filter_topic_{selected_file}"
                            )
                        
                        # Apply filters
                        if selected_tables:
                            df = df[df['source_table'].isin(selected_tables)]
                        if selected_types:
                            df = df[df['type'].isin(selected_types)]
                        
                        # Reorder columns to put source_table first
                        columns = ['source_table', 'name', 'type', 'sql', 'description', 'full_definition']
                        df = df[columns]
                        
                        # Display the table
                        st.dataframe(
                            df,
                            column_config={
                                "source_table": "Source Table",
                                "name": "Field Name",
                                "type": "Type",
                                "sql": "SQL",
                                "description": "Description",
                                "full_definition": st.column_config.Column(
                                    "Full Definition",
                                    help="The complete field definition",
                                    width="large"
                                )
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No fields found in any of the views")
        except Exception as e:
            st.error(f"Error creating fields table: {str(e)}")
            
    elif selected_file.endswith('.view'):
        try:
            view_data = yaml.safe_load(file_content)
            if isinstance(view_data, dict):
                # Get fields from the view
                table_name = selected_file.replace('.view', '')
                if '/' in table_name:  # Remove schema prefix if present
                    table_name = table_name.split('/')[-1]
                    
                fields = get_fields_from_view(view_data, table_name)
                
                if fields:
                    # Create a DataFrame for the table
                    import pandas as pd
                    df = pd.DataFrame(fields)
                    
                    # Add type filter
                    selected_types = st.multiselect(
                        "Filter by Type",
                        options=sorted(df['type'].unique()),
                        placeholder="Select types...",
                        key=f"type_filter_view_{selected_file}"
                    )
                    
                    # Apply filter
                    if selected_types:
                        df = df[df['type'].isin(selected_types)]
                    
                    # Reorder columns to put source_table first
                    columns = ['source_table', 'name', 'type', 'sql', 'description', 'full_definition']
                    df = df[columns]
                    
                    # Display the table
                    st.dataframe(
                        df,
                        column_config={
                            "source_table": "Source Table",
                            "name": "Field Name",
                            "type": "Type",
                            "sql": "SQL",
                            "description": "Description",
                            "full_definition": st.column_config.Column(
                                "Full Definition",
                                help="The complete field definition",
                                width="large"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("No fields found in this view")
                
                # Show YAML view underneath
                st.subheader("YAML View")
                st.code(file_content, language="yaml")
            
        except Exception as e:
            st.error(f"Error creating field table: {str(e)}")
    else:
        # For other files, just show YAML
        st.code(file_content, language="yaml")

st.set_page_config(
    page_title="Omni Model Browser",
    page_icon="🔍",
    layout="wide"
)

# Initialize API client
try:
    api_client = OmniAPIClient()
except ValueError as e:
    st.error(str(e))
    st.stop()

st.title("🔍 Omni Model Browser")

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
                                            display_file_content(selected_topic, yaml_data["files"][selected_topic], yaml_data["files"])
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


# Add the note at the bottom
st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem; font-style: italic;">
        Built on <a href="https://omni.co/" style="color: #666; text-decoration: none;">Omni</a> and vibes ✨
    </div>
""", unsafe_allow_html=True)
