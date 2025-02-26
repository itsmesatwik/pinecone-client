import json

# Read the file
with open('/Users/satwik/Desktop/pleo_json/pleo_data.json', 'r') as file:
    data = json.load(file)

# Process each entry
cleaned_data = []
for entry in data:
    cleaned_entry = {
        'offer_id': entry['offer_id'],
        'offer_name': entry['offer_name'],
        'offer_description': entry['offer_description'],
        'offer_metadata': json.loads(entry['offer_metadata']) if entry['offer_metadata'] else None,
        'mapped_components': json.loads(entry['mapped_components']) if entry['mapped_components'] else []
    }
    cleaned_data.append(cleaned_entry)

# Write the cleaned data back to a new file
with open('/Users/satwik/Desktop/pleo_json/pleo_data_cleaned.json', 'w') as file:
    json.dump(cleaned_data, file, indent=2) 
