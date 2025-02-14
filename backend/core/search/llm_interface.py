from typing import List, Tuple, Optional, Dict, Any
import yaml
import json
import google.generativeai as genai
import os
import sys
import random
from pathlib import Path
from difflib import SequenceMatcher
from dotenv import load_dotenv
from ..utils.text_utils import split_into_sentences, extract_character_name
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
import re
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(env_path)

# Add search directory to path if running standalone
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from .dialog_search import DialogSearchSystem

def handle_gemini_error(retry_state):
    """Log retry attempts for Gemini API calls"""
    exception = retry_state.outcome.exception()
    if exception:
        logger.warning(
            f"Attempt {retry_state.attempt_number} failed with error: {str(exception)}. "
            f"Retrying in {retry_state.next_action.sleep} seconds..."
        )

@retry(
    stop=stop_after_attempt(5),  # Maximum 5 attempts
    wait=wait_exponential(multiplier=1, min=4, max=30),  # Wait between 4 and 30 seconds, doubling each time
    retry=retry_if_exception_type(Exception),  # Retry on any exception
    after=handle_gemini_error,  # Log retry attempts
    reraise=True  # Re-raise the last exception if all retries fail
)
def retry_gemini_call(func, *args, **kwargs):
    """Wrapper to retry Gemini API calls with exponential backoff"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            logger.warning(f"Hit Gemini API rate limit: {str(e)}")
        raise

class LLMInterface:
    def __init__(self, config_path: str):
        """Initialize LLM interface with configuration"""
        # Get project root from environment variable or use Docker default
        project_root = os.getenv('PROJECT_ROOT', '/app')
        logger.debug(f"Using project root: {project_root}")
            
        # Use absolute path for config
        if not os.path.isabs(config_path):
            config_path = os.path.join(project_root, config_path)
            
        logger.debug(f"Loading config from: {config_path}")
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
            
        # Configure Gemini
        genai.configure(api_key=self.config["gemini"]["api_key"])
        
        # Initialize models with specific settings
        match_settings = self.config["gemini"]["models"].get("match_settings", {})
        chat_settings = {
            "temperature": self.config["gemini"]["models"].get("temperature", 0.5),
            "max_output_tokens": self.config["gemini"]["models"].get("max_tokens", 100),
            "presence_penalty": self.config["gemini"]["models"].get("presence_penalty", 0.6),
            "frequency_penalty": self.config["gemini"]["models"].get("frequency_penalty", 0.6)
        }
        
        # Initialize chat model
        self.chat_model = genai.GenerativeModel(
            model_name=self.config["gemini"]["models"]["chat"],
            generation_config=genai.types.GenerationConfig(**chat_settings)
        )
        
        # Initialize match model with more deterministic settings
        self.match_model = genai.GenerativeModel(
            model_name=self.config["gemini"]["models"]["match"],
            generation_config=genai.types.GenerationConfig(
                temperature=match_settings.get("temperature", 0.1),
                max_output_tokens=match_settings.get("max_tokens", 50),
                presence_penalty=match_settings.get("presence_penalty", 0.1),
                frequency_penalty=match_settings.get("frequency_penalty", 0.1)
            )
        )
        
        # Load prompts
        self.prompts = self._load_prompts()
        
        # Initialize different models for different tasks
        self.dialog_model = genai.GenerativeModel(
            model_name=self.config['gemini']['models']['chat'],
            system_instruction=self.prompts['dialog_model']['system_instruction']
        )
        
        self.character_detection_model = genai.GenerativeModel(
            model_name=self.config['gemini']['models']['chat'],
            system_instruction=self.prompts['character_detection_model']['system_instruction']
        )
        
        self.dialog_selector_model = genai.GenerativeModel(
            model_name=self.config['gemini']['models']['chat'],
            system_instruction=self.prompts['dialog_selector_model']['system_instruction']
        )
        
        self.search_system = DialogSearchSystem(config_path)
        
        # Initialize conversation history if enabled
        self.enable_history = True  # Always enable history for better context
        self.max_history = self.config.get('dialog', {}).get('max_history', 10)
        self.conversation_history = []
        self.is_auto_dialog = False
        self.used_dialog_ids = []
        
        # Set up logging
        self.logger = logging.getLogger(__name__)

    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates"""
        project_root = os.getenv('PROJECT_ROOT', '/app')
        logger.debug(f"Using project root for prompts: {project_root}")
        
        prompt_path = os.path.join(project_root, "config", "prompts.yaml")
        logger.debug(f"Loading prompts from: {prompt_path}")
        
        with open(prompt_path) as f:
            return yaml.safe_load(f)
            
    def add_to_history(self, user_input: str, response: str, metadata: dict = None):
        """Add a dialog exchange to history with metadata"""
        if self.enable_history:
            self.logger.info(f"Adding to history - User: {user_input}, Response: {response}")
            self.conversation_history.append({
                "user": user_input,
                "assistant": response,
                "metadata": metadata or {}
            })
            # Keep only the last max_history items
            self.conversation_history = self.conversation_history[-self.max_history:]

    def get_history_context(self, current_message: str = None) -> str:
        """Generate a context string from conversation history"""
        if not self.enable_history and not current_message:
            return ""
            
        context = "\nCONVERSATION HISTORY:\n"
        
        # Add previous complete exchanges
        if self.conversation_history:
            for entry in self.conversation_history:
                context += f"\nDialog: {entry['user']}"
                context += f"\nResponse: {entry['assistant']}"
        
        # Add current message with empty response if provided and not already the last message
        if current_message and (not self.conversation_history or self.conversation_history[-1]["user"] != current_message):
            context += f"\nDialog: {current_message}"
            context += "\nResponse:"
        
        return context

    def _clean_character_names(self, text: str) -> str:
        """Remove character names from dialog text, whether at start or middle of text"""
        # First handle the case where character name is at the start (e.g. "DATA: hello")
        if ':' in text:
            text = text.split(':', 1)[1].strip()
            
        # Then handle cases where character names appear in the middle
        # Look for common character names followed by colon
        character_patterns = [
            r'\s+DATA\s*:', r'\s+PICARD\s*:', r'\s+RIKER\s*:', r'\s+WORF\s*:',
            r'\s+TROI\s*:', r'\s+CRUSHER\s*:', r'\s+LAFORGE\s*:', r'\s+WESLEY\s*:',
            r"\s+O'BRIEN\s*:", r'\s+GUINAN\s*:', r'\s+Q\s*:', r'\s+TASHA\s*:',
            r'\s+COMPUTER\s*:', r'\s+BEVERLY\s*:', r'\s+GEORDI\s*:'
        ]
        
        for pattern in character_patterns:
            text = re.sub(pattern, ' ', text)
            
        # Clean up any extra whitespace
        text = ' '.join(text.split())
        return text

    def generate_and_match(self, message: str) -> Tuple[str, List[Tuple[str, Dict[str, Any]]]]:
        """Generate response and find matching dialog"""
        # Get conversation history context including current message
        history_context = self.get_history_context(current_message=message)
        
        # Build prompt with history (which now includes current message)
        prompt = f"{history_context}\n\nDetect if the dialog necessitates answering as a specific character. If so, respond as that character. If not, choose any characters. In either case, generate 3 different responses that could occur in Star Trek: TNG:"
        
        # Generate responses and get detected character in one call
        detected_character, responses = self._generate_response(prompt, None)
        self.logger.info(f"Detected character for response: {detected_character}")
        
        # Parse the numbered responses
        response_list = []
        for line in responses.split('\n'):
            if line.strip():
                try:
                    _, response = line.split('. ', 1)
                    response_list.append(response)
                except ValueError:
                    continue
                    
        all_matches = []
        # Find matching dialog for each response
        for response in response_list:
            matches = self.search_system.find_similar_dialog(
                query=response,
                character=detected_character,  # Pass detected character to search system
                n_results=40  # Get more matches initially to account for duplicates
            )
            
            # Group matches by text content
            text_to_matches = {}
            for text, metadata in matches:
                # Clean up character names from text
                cleaned_text = self._clean_character_names(text)
                
                if cleaned_text not in text_to_matches:
                    text_to_matches[cleaned_text] = []
                text_to_matches[cleaned_text].append((text, metadata))
            
            # Randomly select one match from each group of duplicates
            unique_matches = []
            for matches_group in text_to_matches.values():
                unique_matches.append(random.choice(matches_group))
            
            # Get up to 20 unique matches
            all_matches.extend(unique_matches[:20])
        
        # Remove duplicates across all responses while preserving order
        # First, group all matches by cleaned text content
        final_text_to_matches = {}
        for match in all_matches:
            text = match[0]
            # Clean up character names from text
            cleaned_text = self._clean_character_names(text)
                
            if cleaned_text not in final_text_to_matches:
                final_text_to_matches[cleaned_text] = []
            final_text_to_matches[cleaned_text].append(match)
        
        # Then randomly select one match from each group and check against used dialogs
        final_matches = []
        for matches_group in final_text_to_matches.values():
            # Keep trying random matches until we find one that hasn't been used
            available_matches = [m for m in matches_group if f"{m[0]}::{m[1].get('clip_path', '')}" not in self.used_dialog_ids]
            if available_matches:
                final_matches.append(random.choice(available_matches))
            else:
                # If all matches in this group have been used, just pick a random one
                final_matches.append(random.choice(matches_group))
        
        # Return all unique matches (up to 60 total), with cleaned text for LLM selection
        cleaned_final_matches = []
        for match in final_matches[:60]:
            text, metadata = match
            # Clean up character names from text
            cleaned_text = self._clean_character_names(text)
            cleaned_final_matches.append((cleaned_text, metadata))
            
        return responses, cleaned_final_matches
        
    def select_best_match(self, message: str, matches: List[Tuple[str, Dict[str, Any]]]) -> int:
        """Select best matching dialog using LLM"""
        if not matches:
            return -1
            
        # Format matches for comparison
        match_texts = [text for text, _ in matches]
        
        # Ensure the current message is in history before we try to update it
        if not self.conversation_history or self.conversation_history[-1]["user"] != message:
            self.add_to_history(message, "", {})
        
        # Get conversation history with current message
        history_context = self.get_history_context(current_message=message)
        
        # Build the full prompt with history (which includes current message)
        prompt = f"""{history_context}

Available responses:
{chr(10).join(f"{i+1}. {text}" for i, text in enumerate(match_texts))}

Select the response number that best responds to the user's message and would create the most natural conversation. Prefer responses that address the user's message directly and don't ask a question, unless the question adds to the conversation. Choose a number between 1 and {len(matches)}."""
        
        # Log the prompt
        self.logger.info("\n=== Dialog Selection Prompt ===")
        self.logger.info(f"Number of candidates: {len(matches)}")
        self.logger.info(f"Prompt:\n{prompt}")
        
        try:
            # Wrap the API call with retry logic
            response = retry_gemini_call(
                self.dialog_selector_model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    candidate_count=1,
                    max_output_tokens=10,
                    top_p=0.1
                )
            ).text
            
            # Clean and validate the response
            try:
                selection = int(response.strip()) - 1
                if 0 <= selection < len(matches):
                    self.logger.info(f"Selected response #{selection + 1}")
                    self.logger.info(f"Selected text: {matches[selection][0]}")
                    
                    # Update the history with the selected response
                    selected_text = matches[selection][0]
                    selected_metadata = matches[selection][1]
                    
                    # Double check that history exists before updating
                    if self.conversation_history:
                        self.conversation_history[-1]["assistant"] = selected_text
                        self.conversation_history[-1]["metadata"] = selected_metadata
                    else:
                        self.add_to_history(message, selected_text, selected_metadata)
                    
                    return selection
                else:
                    self.logger.warning(f"Selected index {selection + 1} out of range, defaulting to first match")
            except ValueError:
                self.logger.warning(f"Could not parse response '{response}' as number, defaulting to first match")
                
        except Exception as e:
            self.logger.error(f"Error selecting match after retries: {e}")
            
        # If anything goes wrong, use the first match
        if matches:
            self.logger.info("Using first match as fallback")
            selected_text = matches[0][0]
            selected_metadata = matches[0][1]
            
            # Double check that history exists before updating
            if self.conversation_history:
                self.conversation_history[-1]["assistant"] = selected_text
                self.conversation_history[-1]["metadata"] = selected_metadata
            else:
                self.add_to_history(message, selected_text, selected_metadata)
            
        return 0  # Default to first match if selection fails
        
    def get_character_suggestions(self, message: str, limit: int = 3) -> List[str]:
        """Get character suggestions based on message content"""
        prompt = self.prompts["suggest_characters"].format(
            message=message,
            limit=limit
        )
        
        try:
            response = self.match_model.generate_content(prompt).text
            return [name.strip() for name in response.split(",")][:limit]
        except Exception as e:
            self.logger.error(f"Error getting character suggestions: {e}")
            return []
            
    def get_episode_context(
        self,
        episode: str,
        start_time: float,
        end_time: float
    ) -> Optional[str]:
        """Get additional episode context for a clip"""
        prompt = self.prompts["get_context"].format(
            episode=episode,
            start_time=start_time,
            end_time=end_time
        )
        
        try:
            return self.chat_model.generate_content(prompt).text
        except Exception as e:
            self.logger.error(f"Error getting episode context: {e}")
            return None

    def _get_character_prompt(self, character_name: str) -> str:
        """Get the character-specific prompt"""
        if character_name:
            return self.prompts['character_prompts']['character_specific'].format(character_name=character_name)
        return self.prompts['character_prompts']['default']

    def _get_auto_dialog_prompt(self) -> str:
        """Get the auto-dialog specific prompt"""
        if not self.is_auto_dialog:
            return ""
        
        return self.prompts['auto_dialog']['prompt']

    def _generate_response(self, user_input: str, character_name: str) -> Tuple[str, str]:
        """Generate multiple responses to user input and detect character if not provided"""
        try:
            # Get appropriate prompt based on character (only if explicitly provided)
            character_prompt = self._get_character_prompt(character_name) if character_name else self._get_auto_dialog_prompt()
            
            # Create the full prompt
            prompt = f"{character_prompt}\n\n{user_input}"
            
            self.logger.info(f"Generate Responses Prompt:\n{prompt}")
            
            # Wrap the API call with retry logic
            response = retry_gemini_call(
                self.dialog_model.generate_content,
                prompt
            ).text
            
            self.logger.debug(f"Raw model response:\n{response}")
            
            # Parse the response to get character and responses
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            detected_character = ""
            numbered_responses = []
            
            # Extract character from first line if present
            if not lines:
                raise ValueError("Empty response from model")
                
            # Look for DETECTED_CHARACTER: prefix
            if not lines[0].startswith("DETECTED_CHARACTER:"):
                self.logger.warning("Response missing DETECTED_CHARACTER: prefix, using default format")
                numbered_responses = lines  # Assume all lines are responses
            else:
                # Extract character from the DETECTED_CHARACTER line
                char_line = lines[0].split(":", 1)[1].strip().upper()
                detected_character = "" if char_line == "NULL" else char_line
                # Rest of the lines should be numbered responses
                numbered_responses = [line for line in lines[1:] if line and not line.startswith("DETECTED_CHARACTER:")]
            
            # Process responses to ensure proper numbering and format
            formatted_responses = []
            for i, line in enumerate(numbered_responses, 1):
                # Remove existing number if present
                if line[0].isdigit() and '. ' in line:
                    line = line.split('. ', 1)[1]
                formatted_responses.append(f"{i}. {line}")
            
            # Ensure we have exactly 3 responses
            while len(formatted_responses) < 3:
                formatted_responses.append(f"{len(formatted_responses) + 1}. {formatted_responses[0].split('. ', 1)[1]}")
            
            # Trim to exactly 3 responses
            formatted_responses = formatted_responses[:3]
            
            # Log the parsed output
            self.logger.debug(f"Parsed character: {detected_character}")
            self.logger.debug(f"Parsed responses:\n" + "\n".join(formatted_responses))
            
            # Return the appropriate character and responses
            if not character_name and detected_character:
                return detected_character, '\n'.join(formatted_responses)
            
            return character_name, '\n'.join(formatted_responses)
                
        except Exception as e:
            self.logger.error(f"Error generating response after retries: {e}")
            return "", "1. I apologize, but I'm having trouble generating a response.\n2. Could you please try rephrasing your message?\n3. Let me try to find a relevant dialog."

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
