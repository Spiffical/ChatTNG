import yaml
from src.search.dialog_storage import DialogStorage

def remove_duplicate_dialogs(config_path: str):
    # Initialize storage
    storage = DialogStorage(config_path)
    
    # Retrieve all dialogs
    all_dialogs = storage.get_all_dialogs()
    if not all_dialogs or not all_dialogs['ids']:
        print("No dialogs found in the database.")
        return
    
    # Use a set to track unique dialogs
    unique_dialogs = set()
    duplicate_ids = []

    # Iterate over all dialogs
    for dialog_id, text in zip(all_dialogs['ids'], all_dialogs['documents']):
        if text in unique_dialogs:
            duplicate_ids.append(dialog_id)
        else:
            unique_dialogs.add(text)
    
    # Remove duplicates
    if duplicate_ids:
        storage.collection.delete(ids=duplicate_ids)
        print(f"Removed {len(duplicate_ids)} duplicate dialogs.")
    else:
        print("No duplicates found.")

if __name__ == '__main__':
    config_path = 'config/app_config.yaml'  # Update with your actual config path
    remove_duplicate_dialogs(config_path)
