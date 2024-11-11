from typing import Optional, Set, Dict, List

class InteractiveMode:
    def __init__(self, interface, player, config):
        self.interface = interface
        self.player = player
        self.config = config
        self.max_history = config.get('modes', {}).get('interactive', {}).get('max_history', 10)
        self.interface.used_dialog_ids = []

    def _add_to_used_dialogs(self, dialog_id: str):
        """Add dialog ID to used list, maintaining max history size"""
        self.interface.used_dialog_ids.append(dialog_id)
        if len(self.interface.used_dialog_ids) > self.max_history:
            self.interface.used_dialog_ids.pop(0)  # Remove oldest dialog

    def run(self):
        """Run the interactive mode"""
        print("\nStar Trek TNG Dialog Interactive System")
        print("Enter your text (or 'quit' to exit):")
        
        while True:
            try:
                user_input = self._get_user_input()
                if user_input is None:
                    break
                
                self._process_input(user_input)
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                print("Please try again.")

    def _get_user_input(self) -> Optional[str]:
        """Get input from user, return None if should quit"""
        user_input = input("\n> ")
        if user_input.lower() == 'quit':
            return None
        return user_input

    def _process_input(self, user_input: str):
        """Process user input and handle response"""
        # Get response and matching dialogs
        generated, matches = self.interface.generate_and_match(user_input)
        print(f"\nGenerated response: {generated}")
        
        if matches:
            print(f"\nTotal matches: {len(matches)}")
            print(f"Recent history: {len(self.interface.used_dialog_ids)}")
            
            # Get best match
            best_match_idx = self.interface.select_best_match(
                user_input,
                matches
            )
            
            if best_match_idx >= 0:
                text, metadata = matches[best_match_idx]
                # Add to used dialogs set with history limit
                dialog_id = self.interface._get_dialog_id(text, metadata)
                self._add_to_used_dialogs(dialog_id)
                
                # Add to conversation history
                if self.interface.enable_history:
                    self.interface.add_to_history(
                        user_input=user_input,
                        response=text,
                        metadata=metadata
                    )
                
                print(f"\nMost relevant dialog found:")
                print(f"Text: {text}")
                print(f"From clip: {metadata['clip_path']}")
                print(f"Time: {metadata['start_time']} - {metadata['end_time']}")
                
                # Play the clip automatically
                print("\nPlaying clip...")
                self.player.play_clip(metadata['clip_path'])
        else:
            print("\nNo matching dialogs found.")
