import pandas as pd
from pydantic import BaseModel
from langchain_community.document_loaders import PDFPlumberLoader
from pathlib import Path
from langchain_core.messages import AIMessage
import json
from src.functions_models import User, Customer, Office, get_llm

def read_file(state):

    if 'file_path' not in state:
        return {'file_content': [{"error": "No file path provided."}]}
    "This node will read the file and extract data from the file path"
    file_path = state['file_path']
    file_ext = Path(file_path).suffix.lower()  # Convert to lowercase for consistent comparison

    if file_ext == '.csv':
        df = pd.read_csv(file_path)
        return {'file_content': df.to_dict(orient="records")}

    if file_ext == '.xlsx':
        df = pd.read_excel(file_path)
        return {'file_content': df.to_dict(orient="records")}

    if file_ext == '.pdf':
        try:
            loader = PDFPlumberLoader(file_path)
            content = loader.load()
            return {'file_content': {"docs":content}}
        except Exception as e:
            return {'file_content': [{"error": f"Failed to read PDF: {str(e)}"}]}
            
    if file_ext == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = json.load(file)
                # If content is not a list, wrap it in a list for consistent processing
                if not isinstance(content, list):
                    content = [content]
                return {'file_content': content}
        except json.JSONDecodeError as e:
            return {'file_content': [{"error": f"Failed to parse JSON: {str(e)}"}]}
        except Exception as e:
            return {'file_content': [{"error": f"Failed to read JSON file: {str(e)}"}]}
            
    if file_ext == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Return content as a list with a single item for consistent processing
                return {'file_content': {"text": content}}
        except Exception as e:
            return {'file_content': [{"error": f"Failed to read text file: {str(e)}"}]}

    return {'file_content': [{"error": f"Failed to read file: {str(e)}", "suggestion": "File might be binary or corrupted"}]}

def interpret(state):
    if 'file_path' not in state:
        return {'result_json': [{"error": "No file content provided."}]}

    prompt_template = """
    Given this raw user data: {chunk}, extract and map it to the Entitylist format.
    Take appropriate instructions from the user input. User Input: {user_input}
    """

    # Define the unique key for each schema
    schema_unique_keys = {
        'customer': 'id',
        'user': 'id',
        'office': 'id'
    }

    # Check if the output schema is valid
    if state['output_schema'] not in schema_unique_keys:
        return {'result_json': [{"error": "Invalid output schema provided."}]}

    unique_key = schema_unique_keys[state['output_schema']]

    # Check if the file content is a list (e.g., from CSV, Excel, or JSON)
    if isinstance(state['file_content'], list):
        # Validate that all entries have the unique key
        for entry in state['file_content']:
            if unique_key not in entry:
                return {'result_json': [{"error": f"Missing unique key '{unique_key}' in the provided file for {state['output_schema']} schema."}]}

        # Split the file content into chunks of 10
        chunks = [state['file_content'][i:i + 5] for i in range(0, len(state['file_content']), 5)]
        combined_entities = []

        for chunk in chunks:
            # Format the prompt for the current chunk
            prompt = prompt_template.format(
                chunk=chunk,
                user_input=state['messages'][-1].content
            )

            # Define the Entitylist class based on the output schema
            if state['output_schema'] == 'customer':
                class Entitylist(BaseModel):
                    entities: list[Customer]
            elif state['output_schema'] == 'user':
                class Entitylist(BaseModel):
                    entities: list[User]
            elif state['output_schema'] == 'office':
                class Entitylist(BaseModel):
                    entities: list[Office]
            else:
                return {'result_json': [{"error": "Invalid output schema provided."}]}

            # Invoke the LLM for the current chunk
            response = get_llm().with_structured_output(Entitylist).invoke(prompt)
            combined_entities.extend(response.entities)

        # Combine all entities into the result_json
        return {'result_json': combined_entities}

    # If the file content is not a list, process it as a single chunk
    prompt = f"""
    Given this raw user data: {state['file_content']}, extract and map it to the Entitylist format.
    Take appropriate instructions from the user input. User Input: {state['messages'][-1].content}
    """
    if state['output_schema'] == 'customer':
        class Entitylist(BaseModel):
            entities: list[Customer]
    elif state['output_schema'] == 'user':
        class Entitylist(BaseModel):
            entities: list[User]
    elif state['output_schema'] == 'office':
        class Entitylist(BaseModel):
            entities: list[Office]
    else:
        return {'result_json': [{"error": "Invalid output schema provided."}]}

    response = get_llm().with_structured_output(Entitylist).invoke(prompt)
    return {'result_json': response.entities}

def add(state):
    if 'file_path' not in state:
        return {'messages': AIMessage(content="Please upload a file for entity addition.")}
    
    if 'error' in state['result_json'][0]:
        error_message = state['result_json'][0]['error']
        return {'messages': AIMessage(content=error_message)}
       
    new_entities = state['result_json']
    new_entities_dicts = [entity.dict() for entity in new_entities]

    if state['output_schema'] == 'user':
        json_file_path = r'database/users.json'
        unique_key = 'id'
    elif state['output_schema'] == 'customer':
        json_file_path = r'database/customers.json'
        unique_key = 'id'
    elif state['output_schema'] == 'office':
        json_file_path = r'database/offices.json'
        unique_key = 'id'

    try:
        with open(json_file_path, 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        # If file doesn't exist, create it with empty list
        existing_data = []

    # Create a dictionary of existing entities for efficient lookup
    existing_entities_dict = {str(entry[unique_key]): entry for entry in existing_data}
    
    # Process each new entity
    added_entities = []
    skipped_entities = []
    
    for entity in new_entities_dicts:
        entity_key = str(entity[unique_key])  # Convert to string for consistent comparison
        if entity_key in existing_entities_dict:
            skipped_entities.append(entity)
        else:
            added_entities.append(entity)
            existing_data.append(entity)

    # Generate appropriate message based on results
    message_parts = []
    if added_entities:
        message_parts.append(f"Successfully added {len(added_entities)} new {state['output_schema']}(s)")
        message_parts.append(f"Added {state['output_schema']}s with {unique_key}s: {[entity[unique_key] for entity in added_entities]}")
    
    if skipped_entities:
        message_parts.append(f"Skipped {len(skipped_entities)} existing {state['output_schema']}(s)")
        message_parts.append(f"Skipped {state['output_schema']}s with {unique_key}s: {[entity[unique_key] for entity in skipped_entities]}")
    
    if added_entities:
        # Only write to file if we actually added something
        with open(json_file_path, 'w') as file:
            json.dump(existing_data, file, indent=4)
    
    message = ". ".join(message_parts) + "."
    return {'messages': AIMessage(content=message)}
