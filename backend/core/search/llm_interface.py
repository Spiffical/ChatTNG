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
            # Check if project_root already contains 'backend'
            if project_root.endswith('backend'):
                config_path = os.path.join(project_root, config_path)
            else:
                # Check if the path already contains 'backend'
                if 'backend' not in config_path.split(os.sep):
                    config_path = os.path.join(project_root, "backend", config_path)
                else:
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
        
        # Try multiple possible paths for the prompts file
        possible_paths = [
            os.path.join(project_root, "config", "prompts.yaml"),  # /app/config/prompts.yaml
            os.path.join(project_root, "backend", "config", "prompts.yaml"),  # /app/backend/config/prompts.yaml
        ]
        
        for prompt_path in possible_paths:
            logger.debug(f"Trying to load prompts from: {prompt_path}")
            try:
                with open(prompt_path) as f:
                    prompts = yaml.safe_load(f)
                    logger.info("=== Loaded Prompts ===")
                    for key, value in prompts.items():
                        if isinstance(value, dict) and 'system_instruction' in value:
                            logger.info(f"\nPrompt '{key}' system instruction:\n{value['system_instruction']}")
                        else:
                            logger.info(f"\nPrompt '{key}':\n{value}")
                    logger.info("=== End Prompts ===")
                    return prompts
            except FileNotFoundError:
                logger.debug(f"Prompts file not found at {prompt_path}")
                continue
            except Exception as e:
                logger.error(f"Error loading prompts from {prompt_path}: {e}")
                raise
                
        # If we get here, we couldn't find the prompts file in any location
        raise FileNotFoundError(f"Could not find prompts.yaml in any of these locations: {', '.join(possible_paths)}")
            
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
        # First, detect if a specific character should respond
        detected_character = self.detect_character(message)
        self.logger.info(f"Detected character for response: {detected_character}")
        
        # Get conversation history context including current message
        history_context = self.get_history_context(current_message=message)
        
        # Generate responses using the detected character
        responses = self.generate_responses(message, detected_character, history_context)
        
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
        # Step 1: Find 40 matching dialogs for each response
        for response in response_list:
            matches = self.search_system.find_similar_dialog(
                query=response,
                character=detected_character,  # Pass detected character to search system
                n_results=40  # Get exactly 40 matches per response
            )
            
            # Step 2: Group matches by exact cleaned text content
            text_to_matches = {}
            for text, metadata in matches:
                # Clean up character names from text
                cleaned_text = self._clean_character_names(text)
                
                if cleaned_text not in text_to_matches:
                    text_to_matches[cleaned_text] = []
                text_to_matches[cleaned_text].append((text, metadata))
            
            # Step 3: For each unique text, randomly select one match
            unique_matches = []
            for matches_group in text_to_matches.values():
                unique_matches.append(random.choice(matches_group))
            
            # Step 4: Take up to 15 unique matches from each response
            all_matches.extend(unique_matches[:15])
        
        # Step 5: Again group all matches by exact cleaned text content
        final_text_to_matches = {}
        for match in all_matches:
            text = match[0]
            # Clean up character names from text
            cleaned_text = self._clean_character_names(text)
                
            if cleaned_text not in final_text_to_matches:
                final_text_to_matches[cleaned_text] = []
            final_text_to_matches[cleaned_text].append(match)
        
        # Step 6: For each unique text, randomly select one match
        deduplicated_matches = []
        for matches_group in final_text_to_matches.values():
            # Keep trying random matches until we find one that hasn't been used
            available_matches = [m for m in matches_group if f"{m[0]}::{m[1].get('clip_path', '')}" not in self.used_dialog_ids]
            if available_matches:
                deduplicated_matches.append(random.choice(available_matches))
            else:
                # If all matches in this group have been used, just pick a random one
                deduplicated_matches.append(random.choice(matches_group))
        
        # Step 7: Extract all previous assistant responses for filtering
        previous_responses = set()
        if self.conversation_history:
            for entry in self.conversation_history:
                if entry.get('assistant'):
                    # Clean the response text for comparison
                    cleaned_response = self._clean_character_names(entry['assistant'])
                    previous_responses.add(cleaned_response)
        
        # Step 8: Filter out any matches that exactly match previous responses
        final_matches = []
        for match in deduplicated_matches:
            text, metadata = match
            cleaned_text = self._clean_character_names(text)
            
            # Skip this match if it exactly matches any previous response
            if cleaned_text in previous_responses:
                continue
            
            final_matches.append((cleaned_text, metadata))
        
        # Return all unique matches (up to 60 total)
        return responses, final_matches[:60]

    def detect_character(self, message: str) -> str:
        """Detect if the message implies a response from a specific character"""
        try:
            # Get conversation history context including current message
            history_context = self.get_history_context(current_message=message)
            
            # Build prompt with history
            prompt = f"""Based on the following conversation history and only based on direct addressing to specific characters in the DIALOG (not responses), determine if a specific character should respond:

{history_context}

Remember to respond ONLY with the character name in uppercase, or "NONE" if no specific character is implied."""
            
            self.logger.info("\n=== Character Detection Debug ===")
            self.logger.info(f"Character detection prompt: {prompt}")
            
            # Wrap the API call with retry logic
            response = retry_gemini_call(
                self.character_detection_model.generate_content,
                prompt
            ).text.strip().upper()
            
            self.logger.info(f"Raw character detection response: {response}")
            
            # Validate the response
            valid_characters = ["PICARD", "DATA", "RIKER", "WORF", "TROI", "CRUSHER", 
                               "LAFORGE", "WESLEY", "GUINAN", "Q", "TASHA", "COMPUTER", "NONE"]
            
            # Extract just the character name if there's additional text
            for character in valid_characters:
                if character in response:
                    response = character
                    break
            
            # If response is not a valid character, return empty string
            if response not in valid_characters:
                self.logger.warning(f"Invalid character detection response: {response}")
                return ""
            
            # Return empty string if NONE was detected
            if response == "NONE":
                return ""
                
            self.logger.info(f"Final detected character: {response}")
            self.logger.info("=== End Character Detection Debug ===\n")
            
            return response
                
        except Exception as e:
            self.logger.error(f"Error detecting character: {e}", exc_info=True)
            return ""

    def generate_responses(self, message: str, character_name: str, history_context: str) -> str:
        """Generate four responses to the message"""
        try:
            # Build prompt with history and character information
            character_info = f"Generate responses as {character_name}." if character_name else "Generate general responses that could be from any character."
            
            prompt = f"""{history_context}

{character_info}
Based on the conversation history and the last message, generate 4 different responses that could occur in Star Trek: TNG, numbered 1-4. Make them with different tones: 1. comedic, 2. serious, 3. philosophical, 4. emotional."""
            
            self.logger.info("\n=== Response Generation Debug ===")
            self.logger.info(f"Response generation prompt: {prompt}")
            
            # Wrap the API call with retry logic
            response = retry_gemini_call(
                self.dialog_model.generate_content,
                prompt
            ).text
            
            self.logger.info(f"Raw response generation response: {response}")
            
            # Process responses to ensure proper numbering and format
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            formatted_responses = []
            
            for line in lines:
                # Check if line starts with a number followed by period
                if line and line[0].isdigit() and '. ' in line:
                    formatted_responses.append(line)
                # Otherwise, add it to the previous response or create a new one
                elif formatted_responses:
                    formatted_responses[-1] += " " + line
                else:
                    formatted_responses.append(f"1. {line}")
            
            # Ensure we have exactly 4 responses
            while len(formatted_responses) < 4:
                if formatted_responses:
                    # Try to extract the content of the first response
                    if '. ' in formatted_responses[0]:
                        first_content = formatted_responses[0].split('. ', 1)[1]
                    else:
                        first_content = formatted_responses[0]
                    formatted_responses.append(f"{len(formatted_responses) + 1}. {first_content}")
                else:
                    formatted_responses.append(f"{len(formatted_responses) + 1}. I'm not sure how to respond to that.")
            
            # Ensure responses are properly numbered
            for i in range(len(formatted_responses)):
                if '. ' in formatted_responses[i]:
                    _, content = formatted_responses[i].split('. ', 1)
                    formatted_responses[i] = f"{i+1}. {content}"
                else:
                    formatted_responses[i] = f"{i+1}. {formatted_responses[i]}"
            
            # Trim to exactly 4 responses
            formatted_responses = formatted_responses[:4]
            
            self.logger.info(f"Final formatted responses:\n" + "\n".join(formatted_responses))
            self.logger.info("=== End Response Generation Debug ===\n")
            
            return '\n'.join(formatted_responses)
                
        except Exception as e:
            self.logger.error(f"Error generating responses: {e}", exc_info=True)
            return "1. I apologize, but I'm having trouble generating a response.\n2. Could you please try rephrasing your message?\n3. Let me try to find a relevant dialog.\n4. Perhaps we can discuss something else."

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

Select the response number that best responds to the user's message and would create the most natural conversation. Prefer responses that address the user's message directly and don't ask a question, unless the question adds to the conversation. 
Do NOT choose a response that is identical to any message in the conversation history. Choose a number between 1 and {len(matches)}."""
        
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

    def generate_response(self, message: str, character_name: str = None) -> Tuple[str, str]:
        """Generate a response to the message"""
        try:
            # Get conversation history context including current message
            history_context = self.get_history_context(current_message=message)
            
            # Generate responses using the detected character
            responses = self.generate_responses(message, character_name, history_context)
            
            # Parse the numbered responses
            formatted_responses = []
            for line in responses.split('\n'):
                if line.strip():
                    try:
                        _, response = line.split('. ', 1)
                        formatted_responses.append(response)
                    except ValueError:
                        continue
            
            # Ensure we have at least one response
            if not formatted_responses:
                formatted_responses = ["I'm not sure how to respond to that."]
            
            # Trim to exactly 4 responses
            formatted_responses = formatted_responses[:4]
            
            # Log the final output
            self.logger.info("=== Final Output ===")
            self.logger.info(f"Final character: {character_name}")
            self.logger.info(f"Final responses:\n" + "\n".join(formatted_responses))
            self.logger.info("=== End Generate Response Debug ===\n")
            
            return character_name, '\n'.join(formatted_responses)
                
        except Exception as e:
            self.logger.error(f"Error generating response after retries: {e}", exc_info=True)
            return "", "1. I apologize, but I'm having trouble generating a response.\n2. Could you please try rephrasing your message?\n3. Let me try to find a relevant dialog.\n4. Perhaps we can discuss something else."

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
