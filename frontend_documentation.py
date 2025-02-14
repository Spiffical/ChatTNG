import os

def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

def write_frontend_docs():
    # First write the documentation
    with open('frontend_complete.md', 'w', encoding='utf-8') as f:
        # Write documentation section
        f.write("""# ChatTNG Frontend Documentation

## Overview
ChatTNG is a modern web application built with React, TypeScript, and Vite. The frontend uses Mantine UI components for a polished user interface and implements a chat interface with video playback capabilities.

## Tech Stack
- React + TypeScript
- Vite (Build tool)
- Mantine UI Framework
- React Query for API state management
- Axios for HTTP requests
- Video.js for video playback

## Core Components

### 1. App Component (`App.tsx`)
The root component that sets up:
- MantineProvider for UI theming
- QueryClientProvider for API state management
- Notifications system
- Main ChatInterface component

### 2. Chat Interface (`ChatInterface.tsx`)
The main chat component that handles:
- Message display and scrolling
- User input handling
- API integration for chat functionality
- Conversation management
- Real-time updates

Key features:
- Responsive layout with scroll area for messages
- Message input with send button
- Error handling and notifications
- Automatic scrolling to new messages
- Video clip integration

### 3. Chat Message (`ChatMessage.tsx`)
Individual message component that displays:
- User/Assistant avatars
- Message content
- Video clips (when present)
- Subtitle support
- Metadata for clips (season, episode, character)

### 4. Video Player (`VideoPlayer.tsx`)
Custom video player component with:
- HTML5 video support
- Subtitle handling (SRT to VTT conversion)
- Error handling
- Autoplay support
- Cross-origin resource handling

## Styling
The application uses a combination of:
- Mantine UI components for consistent design
- Custom CSS for specific styling needs
- Responsive design principles
- Modern UI elements (shadows, borders, transitions)

## API Integration
- Base URL: http://localhost:8000/api
- Endpoints:
  - POST /chat/conversations - Create new conversation
  - GET /chat/conversations/{id} - Get conversation messages
  - POST /chat/conversations/{id}/messages - Send message

## Key Features
1. Real-time chat interface
2. Video clip playback
3. Subtitle support
4. Error handling and notifications
5. Responsive design
6. Modern UI/UX
7. Type safety with TypeScript
8. State management with React Query

## Project Structure
```
frontend/chattng-web/
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx
│   │   ├── ChatMessage.tsx
│   │   └── VideoPlayer.tsx
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── package.json
└── vite.config.ts
```

## Development Setup
1. Node.js environment
2. Package management with npm/yarn
3. Development server with Vite
4. TypeScript compilation
5. ESLint for code quality

## UI/UX Features
1. Clean, modern interface
2. Responsive design
3. Smooth animations
4. Error feedback
5. Loading states
6. Video playback controls
7. Message threading
8. Avatar system for users/assistant

## Performance Considerations
1. React Query for efficient API caching
2. Optimized video playback
3. Lazy loading of components
4. Efficient state management
5. Debounced user input
6. Optimized rendering with React

---

# Source Code

""")

        # List of frontend files to include
        frontend_files = [
            'frontend/chattng-web/src/App.tsx',
            'frontend/chattng-web/src/main.tsx',
            'frontend/chattng-web/src/components/ChatInterface.tsx',
            'frontend/chattng-web/src/components/ChatMessage.tsx',
            'frontend/chattng-web/src/components/VideoPlayer.tsx',
            'frontend/chattng-web/src/App.css',
            'frontend/chattng-web/src/index.css',
            'frontend/chattng-web/package.json',
            'frontend/chattng-web/vite.config.ts',
            'frontend/chattng-web/tsconfig.json',
            'frontend/chattng-web/tsconfig.app.json',
            'frontend/chattng-web/tsconfig.node.json'
        ]

        # Write each file's contents
        for file_path in frontend_files:
            f.write(f"\n## {file_path}\n")
            f.write("```" + file_path.split('.')[-1] + "\n")  # Add language for syntax highlighting
            content = read_file_content(file_path)
            f.write(content)
            f.write("\n```\n")

if __name__ == "__main__":
    write_frontend_docs()
    print("Frontend documentation and source code have been written to 'frontend_complete.md'") 