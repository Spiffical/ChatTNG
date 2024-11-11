import random
from typing import Tuple, List, Dict, Set

class AutoDialogMode:
    def __init__(self, interface, player, config):
        self.interface = interface
        self.player = player
        self.config = config
        self.delay = config.get('modes', {}).get('auto_dialog', {}).get('delay_between_responses', 2.0)
        self.max_exchanges = config.get('modes', {}).get('auto_dialog', {}).get('max_exchanges', 10)
        self.max_history = config.get('modes', {}).get('auto_dialog', {}).get('max_history', 10)
        self.interface.is_auto_dialog = True
        self.interface.used_dialog_ids = []

    def get_random_dialog(self) -> Tuple[str, Dict]:
        """Get a random dialog from the database that hasn't been used"""
        all_dialogs = self.interface.search_system.collection.get()
        if not all_dialogs or not all_dialogs['ids']:
            raise ValueError("No dialogs found in database")
        
        # Filter out used dialogs
        available_indices = [
            i for i in range(len(all_dialogs['documents']))
            if self.interface._get_dialog_id(all_dialogs['documents'][i], all_dialogs['metadatas'][i]) not in self.interface.used_dialog_ids
        ]
        
        print(f"\nTotal dialogs: {len(all_dialogs['documents'])}")
        print(f"Used dialogs: {len(self.interface.used_dialog_ids)}")
        print(f"Available dialogs: {len(available_indices)}")
        
        if not available_indices:
            print("\nAll dialogs have been used, starting fresh...")
            self.interface.used_dialog_ids.clear()
            available_indices = range(len(all_dialogs['ids']))
        
        idx = random.choice(available_indices)
        dialog_id = self.interface._get_dialog_id(all_dialogs['documents'][idx], all_dialogs['metadatas'][idx])
        self.interface.used_dialog_ids.append(dialog_id)
        
        print(f"\nSelected dialog ID: {dialog_id}")
        return all_dialogs['documents'][idx], all_dialogs['metadatas'][idx]

    def run(self):
        """Run the auto-dialog mode"""
        print("\nEntering Auto-Dialog Mode (Press Ctrl+C to exit)")
        exchanges = 0
        
        try:
            # Start with a random dialog
            current_text, metadata = self.get_random_dialog()
            
            while exchanges < self.max_exchanges:
                print("\n=== Exchange Debug ===")
                print(f"Exchange #: {exchanges + 1}")
                print(f"Current text: {current_text}")
                print(f"Current clip: {metadata['clip_path']}")
                
                # Play clip first
                print(f"\nPlaying clip...")
                self.player.play_clip(metadata['clip_path'])
                
                # Generate response and find matching dialog
                generated, matches = self.interface.generate_and_match(current_text)
                print(f"\nGenerated response: {generated}")
                print(f"Found {len(matches)} potential matches")
                
                if not matches:
                    print("\nNo matches found. Starting new conversation...")
                    current_text, metadata = self.get_random_dialog()
                    continue
                    
                # Get best match
                best_match_idx = self.interface.select_best_match(
                    current_text,
                    matches
                )
                
                if best_match_idx < 0:
                    print("\nNo valid match found. Starting new conversation...")
                    current_text, metadata = self.get_random_dialog()
                    continue
                    
                next_text, next_metadata = matches[best_match_idx]
                dialog_id = self.interface._get_dialog_id(next_text, next_metadata)
                
                # Add to used dialogs
                self.interface.used_dialog_ids.append(dialog_id)
                
                print("\n=== Selected Response Debug ===")
                print(f"Selected text: {next_text}")
                print(f"Selected clip: {next_metadata['clip_path']}")
                print(f"Dialog ID: {dialog_id}")
                print(f"Total used dialogs: {len(self.interface.used_dialog_ids)}")
                
                # Add the clip dialog exchange to history
                if self.interface.enable_history:
                    self.interface.add_to_history(
                        user_input=current_text,
                        response=next_text,
                        metadata=next_metadata
                    )
                
                current_text, metadata = next_text, next_metadata
                exchanges += 1
                
        except KeyboardInterrupt:
            print("\nExiting Auto-Dialog Mode...")
            print("\nFinal list of used dialogs:")
            for dialog_id in sorted(self.interface.used_dialog_ids):
                print(f"- {dialog_id}")
