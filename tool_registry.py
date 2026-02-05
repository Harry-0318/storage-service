from sqlalchemy import Table, Column, Integer, String, Boolean, JSON, TIMESTAMP, MetaData, func, Float

# Mapping from JSON schema type strings to SQLAlchemy types
TYPE_MAPPING = {
    "int": Integer,
    "integer": Integer,
    "str": String,
    "string": String,
    "bool": Boolean,
    "boolean": Boolean,
    "json": JSON,
    "float": Float,
    "timestamp": TIMESTAMP
}

def validate_schema(schema_definition: list) -> bool:
    """
    Validates the schema definition list.
    Expected format: [{"name": "field_name", "type": "str"}, ...]
    """
    if not isinstance(schema_definition, list):
        raise ValueError("Schema must be a list of fields")
    
    for field in schema_definition:
        if not isinstance(field, dict) or "name" not in field or "type" not in field:
            raise ValueError("Each field must have 'name' and 'type'")
        
        field_type = field["type"].lower()
        if field_type not in TYPE_MAPPING:
            raise ValueError(f"Unsupported type: {field_type}. Allowed: {list(TYPE_MAPPING.keys())}")
            
    return True

def validate_payload(payload: dict, schema_definition: list) -> bool:
    """
    Validates that the payload matches the schema types.
    This is a basic validation. 
    """
    schema_map = {f["name"]: f["type"].lower() for f in schema_definition}
    
    for key, value in payload.items():
        if key not in schema_map:
            # Extra fields are silently ignored (flexible mode).
            # To enforce strict mode, uncomment:
            # raise ValueError(f"Unknown field: {key}")
            pass

        # check types if key matches
        if key in schema_map:
            expected_type = schema_map[key]
            if expected_type in ["int", "integer"] and not isinstance(value, int):
                raise ValueError(f"Field '{key}' expected int, got {type(value)}")
            if expected_type in ["str", "string"] and not isinstance(value, str):
                raise ValueError(f"Field '{key}' expected str, got {type(value)}")
            if expected_type in ["bool", "boolean"] and not isinstance(value, bool):
                 raise ValueError(f"Field '{key}' expected bool, got {type(value)}")
    
    return True

def create_tool_table(tool_name: str, schema_definition: list, metadata: MetaData) -> Table:
    """
    Dynamically creates a SQLAlchemy Table object based on the tool name and schema.
    """
    table_name = f"tool_{tool_name}"
    
    columns = [
        Column("id", Integer, primary_key=True, index=True),
        Column("created_at", TIMESTAMP, server_default=func.now())
    ]
    
    for field in schema_definition:
        col_name = field["name"]
        col_type_str = field["type"].lower()
        col_type = TYPE_MAPPING.get(col_type_str, String)
        
        # We can add more specific column options from schema if needed (nullable, etc)
        columns.append(Column(col_name, col_type))
        
    table = Table(table_name, metadata, *columns, extend_existing=True)
    return table
