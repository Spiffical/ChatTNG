from typing import List, Tuple, Optional, Dict
import yaml
from openai import OpenAI
import os
import sys
from pathlib import Path
from difflib import SequenceMatcher
from src.utils.text_utils import split_into_sentences

# Add search directory to path if running standalone
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from src.search.dialog_search import DialogSearchSystem
from src.utils.text_utils import extract_character_name

class LLMInterface:
    def __init__(self, config_path: str):
        """Initialize the LLM interface with configuration"""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.client = OpenAI(api_key=self.config['openai']['api_key'])
        self.search_system = DialogSearchSystem(config_path)
        
        # Initialize conversation history if enabled
        self.enable_history = self.config.get('dialog', {}).get('enable_history', False)
        self.max_history = self.config.get('dialog', {}).get('max_history', 10)
        self.conversation_history = []
        self.is_auto_dialog = False
        self.used_dialog_ids = []  # Initialize used_dialog_ids list

    def add_to_history(self, user_input: str, response: str, metadata: dict = None):
        """Add a dialog exchange to history with metadata"""
        if self.enable_history:
            self.conversation_history.append({
                "user": user_input,
                "assistant": response,
                "metadata": metadata or {}
            })
            # Keep only the last max_history items
            self.conversation_history = self.conversation_history[-self.max_history:]

    def get_history_context(self) -> str:
        """Generate a context string from conversation history"""
        if not self.enable_history or not self.conversation_history:
            return ""
            
        context = "\nPrevious conversation:\n"
        for entry in self.conversation_history:
            context += f"Dialog: {entry['user']}\n"
            context += f"Response: {entry['assistant']}\n\n"
        
        return context

    def generate_and_match(self, user_input: str, style: str = "humorous") -> Tuple[str, List[Tuple[str, dict]]]:
        """
        Generate a response and find the most similar actual dialogs.
        Returns (generated_response, [(matching_dialog, metadata), ...]) tuple.
        """
        # Get used dialogs from the current mode or use internal list
        used_dialogs = getattr(self, 'used_dialog_ids', [])
        if used_dialogs:
            print("\nCurrently used dialogs:")
            for dialog in used_dialogs:
                print(f"- {dialog}")
        
        # Cache character detection result
        character_name = self.detect_character_context(user_input)
        
        # Generate response with cached character_name
        generated_text = self._generate_response(user_input, character_name)
        
        # Request matches with filtering already applied
        filtered_dialogs = self.search_system.find_similar_dialog(
            generated_text,
            character_name=character_name,
            n_results=20,
            used_dialogs=used_dialogs
        )
        
        print(f"\nFiltered to {len(filtered_dialogs)} unique dialogs")
        return generated_text, filtered_dialogs

    def _get_character_prompt(self, character_name: str) -> str:
        """Get the character-specific prompt"""
        if character_name:
            return f"\nYou should respond as {character_name} from Star Trek: TNG, matching their personality and speech patterns."
        return "You should respond primarily as someone not on board the Enterprise, i.e. not a Starfleet officer."

    def _get_auto_dialog_prompt(self) -> str:
        """Get the auto-dialog specific prompt"""
        if not self.is_auto_dialog:
            return ""
        
        return """
You are in auto-dialog mode:
- Avoid simple confirmations or one-word responses
- Ask questions that advance the conversation
- Reference previous context when appropriate
- Introduce new topics or perspectives related to the conversation
- Express opinions or emotions that invite further discussion
- Use statements that create opportunities for follow-up responses"""

    def _generate_response(self, user_input: str, character_name: str) -> str:
        """Generate a response using the LLM"""
        character_prompt = self._get_character_prompt(character_name)
        auto_dialog_prompt = self._get_auto_dialog_prompt()
        
        system_prompt = f"""You are a character from Star Trek: The Next Generation.
Your task is to provide a response that matches the style and tone of the show.

Guidelines:
- Keep responses concise but engaging
- Do not address the user as "captain" or any title, unless they explicitly say who they are
- Do not start your response with "Computer", unless it absolutely makes sense to do so
- Answer questions directly while leaving room for conversation to continue
- {character_prompt}
- Don't mention that you're an AI or that this is a simulation
- Try to keep answers to one sentence
{auto_dialog_prompt}
{self.get_history_context()}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.config['openai']['models']['chat'],
                messages=messages,
                temperature=self.config['openai']['models']['temperature'],
                max_tokens=self.config['openai']['models']['max_tokens'],
                presence_penalty=self.config['openai']['models']['presence_penalty'],
                frequency_penalty=self.config['openai']['models']['frequency_penalty']
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I am unable to process your request at this time."

    def select_best_match(self, user_input: str, matches: list) -> int:
        """
        Use LLM to select the best matching dialog from the options.
        Returns the index of the best match (0-based).
        """
        if not matches:
            return -1

        # Get conversation history context
        history_context = self.get_history_context()
        
        system_prompt = """You are a dialog selection assistant for Star Trek: TNG. Given a user's input, 
        conversation history, and several dialog options, select the dialog option that best matches the 
        context and intent of the conversation.

        Consider:
        1. Relevance to the current topic
        2. Thematic consistency with previous exchanges
        3. Character continuity if a specific character is involved
        4. Natural conversation flow
        5. Contextual appropriateness
        
        Respond ONLY with the number of the best matching dialog. No other text."""

        # Format the dialog options
        dialog_options = "\n".join([
            f"{i+1}. {match[0]}" for i, match in enumerate(matches)
        ])

        print(f"\nDialog options:\n{dialog_options}")

        user_message = f"""Conversation History:
{history_context}

Current Input: {user_input}

Dialog Options:
{dialog_options}

Which dialog option (1-{len(matches)}) best continues this conversation while maintaining context and flow?"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.3,
                max_tokens=10
            )
            
            choice_text = response.choices[0].message.content.strip()
            try:
                choice = int(choice_text)
                if 1 <= choice <= len(matches):
                    return choice - 1
            except ValueError:
                pass
            
            return 0 if matches else -1
            
        except Exception as e:
            print(f"Error selecting best match: {e}")
            return 0 if matches else -1

    def detect_character_context(self, user_input: str) -> str:
        """Use LLM to detect if response should come from a specific character"""
        character_names = ["PICARD", "DATA", "RIKER", "WORF", "TROI", "CRUSHER", "LAFORGE", 
                           "WESLEY", "GUINAN", "Q", "TASHA", "COMPUTER"]

        system_prompt = """You are a Star Trek: TNG dialog analyzer. Your task is to determine if the given input or context 
        implies that the response should come from a specific character.

        CHARACTER NAMES: {character_names}

        Respond ONLY with the character name in uppercase, or "NONE" if no specific character is implied.
        Consider:
        1. Direct addressing (e.g., "Data, what do you think?", "Computer, what is the status of the warp core?")
        2. Context clues (e.g., "What would the ship's counselor say about this?")
        3. Previous conversation context"""

        print("\n=== Character Detection ===")
        print(f"Input: {user_input}")
        print(f"Context: {self.get_history_context()}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Input: {user_input}\nContext:{self.get_history_context()}"}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            character = response.choices[0].message.content.strip().upper()
            if character != "NONE" and character in character_names:
                print(f"✓ Detected character: {character}")
                return character
            else:
                print("✗ No specific character detected")
                return ""
            
        except Exception as e:
            print(f"! Error detecting character context: {e}")
            return ""

    def _get_dialog_id(self, text: str, metadata: Dict) -> str:
        """Create a unique identifier for a dialog using its text and clip path"""
        clip_path = metadata.get('clip_path', '')
        return f"{text}::{clip_path}"

    def add_used_dialog(self, text: str, metadata: dict):
        """Add a dialog to the used dialogs list"""
        dialog_id = self._get_dialog_id(text, metadata)
        if dialog_id not in self.used_dialog_ids:
            self.used_dialog_ids.append(dialog_id)

def main():
    """Simple CLI interface for testing"""
    import argparse
    parser = argparse.ArgumentParser(description='Star Trek TNG Dialog Generator')
    parser.add_argument('--config', required=True, help='Path to config file')
    args = parser.parse_args()

    interface = LLMInterface(args.config)
    
    print("Enter your text (or 'quit' to exit):")
    while True:
        user_input = input("> ")
        if user_input.lower() == 'quit':
            break
        
        generated, match = interface.generate_and_match(user_input)
        print(f"\nGenerated response: {generated}")
        if match:
            print(f"Similar dialog found:")
            for i, (text, metadata) in enumerate(match):
                print(f"Text {i+1}: {text}")
                print(f"From clip: {metadata['clip_path']}")
                print(f"Time: {metadata['start_time']} - {metadata['end_time']}")
        print()

if __name__ == "__main__":
    main()
