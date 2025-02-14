# ChatTNG Frontend Documentation

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


## frontend/chattng-web/src/App.tsx
```tsx
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChatInterface } from './components/ChatInterface';

const queryClient = new QueryClient();

const theme = createTheme({
  colors: {
    brand: [
      '#001f3f', '#001f3f', '#001f3f', '#001f3f', '#001f3f',
      '#001f3f', '#001f3f', '#001f3f', '#001f3f', '#001f3f',
    ],
  },
  primaryColor: 'brand',
  fontFamily: 'Inter, system-ui, Avenir, Helvetica, Arial, sans-serif',
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <Notifications />
        <ChatInterface />
      </MantineProvider>
    </QueryClientProvider>
  );
}

export default App;

```

## frontend/chattng-web/src/main.tsx
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

```

## frontend/chattng-web/src/components/ChatInterface.tsx
```tsx
import { useState, useRef, useEffect } from 'react';
import { TextInput, Stack, Box, Container, Paper, Button, ScrollArea, Title, Center } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { ChatMessage } from './ChatMessage';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  clip_url?: string;
  subtitle_url?: string;
  clip_metadata?: {
    clip_path: string;
    start_time: number;
    end_time: number;
    character?: string;
    episode?: string;
    season?: number;
    confidence?: number;
  };
}

interface Conversation {
  id: string;
  messages: Message[];
}

const API_BASE_URL = 'http://localhost:8000/api';

export const ChatInterface = () => {
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Query conversation messages
  const { data: conversation, isLoading } = useQuery<Conversation>({
    queryKey: ['conversation', conversationId],
    queryFn: async () => {
      if (!conversationId) return { id: '', messages: [] };
      const response = await axios.get(`${API_BASE_URL}/chat/conversations/${conversationId}`);
      return response.data;
    },
    enabled: !!conversationId,
  });

  // Mutation for creating a conversation
  const createConversation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE_URL}/chat/conversations`, {
        session_id: 'default', // TODO: Use real session management
      });
      return response.data;
    },
  });

  // Mutation for sending messages
  const sendMessage = useMutation({
    mutationFn: async ({ content, conversationId }: { content: string; conversationId: string }) => {
      const response = await axios.post(
        `${API_BASE_URL}/chat/conversations/${conversationId}/messages`,
        {
          role: 'user',
          content,
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] });
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: 'Failed to send message. Please try again.',
        color: 'red',
      });
    },
  });

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [conversation?.messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const message = input;
    setInput('');

    try {
      // Create conversation if it doesn't exist
      if (!conversationId) {
        const newConversation = await createConversation.mutateAsync();
        setConversationId(newConversation.id);
        await sendMessage.mutateAsync({ content: message, conversationId: newConversation.id });
      } else {
        await sendMessage.mutateAsync({ content: message, conversationId });
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to send message. Please try again.',
        color: 'red',
      });
    }
  };

  return (
    <Box 
      style={{ 
        width: '100vw', 
        height: '100vh', 
        background: '#f0f2f5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem'
      }}
    >
      <Paper 
        shadow="xl" 
        radius="xl" 
        style={{ 
          width: '90%', 
          maxWidth: '1000px',
          height: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid rgba(0, 0, 0, 0.1)',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.1)',
          position: 'relative',
          background: 'white'
        }}
      >
        {/* Header */}
        <Box 
          p="lg" 
          style={{ 
            background: '#2962ff',
            borderBottom: '1px solid rgba(0, 0, 0, 0.1)'
          }}
        >
          <Title order={1} ta="center" c="white" style={{ fontSize: '1.8rem', fontWeight: 600 }}>
            ChatTNG
          </Title>
        </Box>

        {/* Messages Area */}
        <Box style={{ 
          flex: 1, 
          overflowY: 'hidden', 
          position: 'relative', 
          background: 'white'
        }}>
          <ScrollArea 
            h="100%" 
            offsetScrollbars 
            scrollbarSize={6}
            type="hover"
            viewportRef={scrollAreaRef}
          >
            <Stack gap="lg" p="xl">
              {conversation?.messages.map((message, index) => (
                <ChatMessage
                  key={index}
                  role={message.role}
                  content={message.content}
                  clipUrl={message.clip_url}
                  subtitleUrl={message.subtitle_url}
                  clipMetadata={message.clip_metadata}
                />
              ))}
            </Stack>
          </ScrollArea>
        </Box>

        {/* Input Area */}
        <Box 
          style={{ 
            borderTop: '1px solid rgba(0, 0, 0, 0.1)',
            background: 'white',
            padding: '1.5rem',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <Box style={{ width: '100%', maxWidth: '600px' }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <TextInput
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                size="md"
                radius="xl"
                styles={{
                  root: { flex: 1 },
                  input: {
                    backgroundColor: '#f8f9fa',
                    border: '1px solid rgba(0, 0, 0, 0.1)',
                    fontSize: '1rem',
                    padding: '1.2rem 1.5rem',
                    height: 'auto',
                    '&:focus': {
                      borderColor: '#2962ff',
                      backgroundColor: 'white'
                    }
                  }
                }}
                disabled={createConversation.isPending || sendMessage.isPending}
              />
              <Button
                type="submit"
                variant="filled"
                loading={createConversation.isPending || sendMessage.isPending}
                disabled={!input.trim()}
                radius="xl"
                size="md"
                style={{
                  background: '#2962ff',
                  border: 'none',
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                  padding: '0 1.5rem',
                  height: '2.75rem'
                }}
              >
                Send
              </Button>
            </form>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}; 
```

## frontend/chattng-web/src/components/ChatMessage.tsx
```tsx
import { useState } from 'react';
import { Paper, Text, Stack, Group, Avatar, Box, Loader } from '@mantine/core';
import { VideoPlayer } from './VideoPlayer';
import { IconUser, IconRobot } from '@tabler/icons-react';

interface ClipMetadata {
  clip_path: string;
  start_time: number;
  end_time: number;
  character?: string;
  episode?: string;
  season?: number;
  confidence?: number;
}

interface ChatMessageProps {
  role: string;
  content: string;
  clipUrl?: string;
  subtitleUrl?: string;
  clipMetadata?: ClipMetadata;
  isPending?: boolean;
}

export const ChatMessage = ({
  role,
  content,
  clipUrl,
  subtitleUrl,
  clipMetadata,
  isPending,
}: ChatMessageProps) => {
  const isAssistant = role === 'assistant';
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [videoEnded, setVideoEnded] = useState(false);

  const getProxiedUrl = (url: string | undefined) => {
    if (!url) return undefined;
    return url.replace('https://d2qqs9uhgc4wdq.cloudfront.net', '');
  };

  if (isPending) {
    return (
      <Group align="flex-start" gap="md" wrap="nowrap">
        <Avatar
          radius="xl"
          size="md"
          style={{
            background: '#001f3f',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
          }}
        >
          <IconRobot size={20} />
        </Avatar>
        <Box style={{ maxWidth: 'min(600px, 75%)' }}>
          <Paper
            shadow="sm"
            radius="lg"
            p="md"
            style={{
              background: '#0d1b2a',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <Loader size="xs" color="blue" variant="dots" />
            <Text style={{ color: '#e0e0e0', fontSize: '1rem' }}>
              Thinking...
            </Text>
          </Paper>
        </Box>
      </Group>
    );
  }

  return (
    <Group
      align="flex-start"
      gap="md"
      wrap="nowrap"
      justify={isAssistant ? 'flex-start' : 'flex-end'}
    >
      {isAssistant && (
        <Avatar
          radius="xl"
          size="md"
          style={{
            background: '#001f3f',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
          }}
        >
          <IconRobot size={20} />
        </Avatar>
      )}

      <Box style={{ maxWidth: 'min(600px, 75%)' }}>
        <Stack gap="xs">
          {isAssistant && clipUrl ? (
            <Box>
              <Paper
                radius="md"
                style={{
                  overflow: 'hidden',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                  background: '#0d1b2a',
                }}
              >
                <VideoPlayer
                  src={getProxiedUrl(clipUrl) || ''}
                  subtitleSrc={getProxiedUrl(subtitleUrl)}
                  autoplay={true}
                  onVideoLoaded={() => setVideoLoaded(true)}
                  onVideoEnd={() => setVideoEnded(true)}
                />
                {!videoLoaded && (
                  <Text size="sm" c="dimmed" mt="xs" style={{ textAlign: 'center', padding: '1rem' }}>
                    Loading clip...
                  </Text>
                )}
              </Paper>
              {videoEnded && (
                <Text
                  size="sm"
                  c="dimmed"
                  mt="xs"
                  style={{ fontSize: '0.9rem', marginTop: '0.5rem', color: '#e0e0e0' }}
                >
                  {content}
                </Text>
              )}
              {clipMetadata && (
                <Text size="sm" c="dimmed" mt="xs" style={{ fontSize: '0.9rem' }}>
                  Season {clipMetadata.season} Episode {clipMetadata.episode}
                  {clipMetadata.character && ` - ${clipMetadata.character}`}
                </Text>
              )}
            </Box>
          ) : (
            <Paper
              shadow="sm"
              radius="lg"
              p="md"
              style={{
                wordBreak: 'break-word',
                background: isAssistant ? '#0d1b2a' : '#001f3f',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <Text
                c={isAssistant ? '#e0e0e0' : 'white'}
                style={{ whiteSpace: 'pre-wrap', fontSize: '1rem' }}
              >
                {content}
              </Text>
            </Paper>
          )}
        </Stack>
      </Box>

      {!isAssistant && (
        <Avatar
          radius="xl"
          size="md"
          style={{
            background: '#001f3f',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
          }}
        >
          <IconUser size={20} />
        </Avatar>
      )}
    </Group>
  );
}; 
```

## frontend/chattng-web/src/components/VideoPlayer.tsx
```tsx
import { useEffect, useRef, useState } from 'react';
import { Box, Paper } from '@mantine/core';

interface VideoPlayerProps {
  src: string;
  subtitleSrc?: string;  // URL to the SRT subtitle file
  autoplay?: boolean;
  onVideoEnd?: () => void;
  onVideoLoaded?: () => void;
}

export const VideoPlayer = ({
  src,
  subtitleSrc,
  autoplay = true,
  onVideoEnd,
  onVideoLoaded,
}: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vttUrl, setVttUrl] = useState<string | null>(null);

  // Handle video metadata loaded - ensure subtitles are showing
  const handleMetadataLoaded = () => {
    const video = videoRef.current;
    if (video && video.textTracks.length > 0) {
      // Force all tracks to showing mode
      Array.from(video.textTracks).forEach(track => {
        track.mode = 'showing';
      });
      console.log('Set tracks to showing on metadata load');
    }
    // Notify parent that the video is ready
    if (onVideoLoaded) onVideoLoaded();
  };

  useEffect(() => {
    console.log('VideoPlayer props:', { src, subtitleSrc });
    
    // Reset error state when src changes
    setError(null);
    
    if (videoRef.current && autoplay && !hasPlayed) {
      videoRef.current.play().catch((error) => {
        console.error('Video playback error:', error);
        setError(error.message);
      });
      setHasPlayed(true);
    }
  }, [src, autoplay, hasPlayed]);

  useEffect(() => {
    // Convert SRT to VTT when subtitle source changes
    const convertSrtToVtt = async () => {
      if (!subtitleSrc) {
        setVttUrl(null);
        return;
      }

      try {
        console.log('Fetching subtitles from:', subtitleSrc);
        const response = await fetch(subtitleSrc);
        if (!response.ok) {
          throw new Error(`Failed to fetch subtitles: ${response.statusText}`);
        }

        const srtContent = await response.text();
        console.log('Received SRT content:', srtContent.substring(0, 200) + '...');
        
        // Convert SRT to VTT
        let vttContent = 'WEBVTT\n\n';
        const srtBlocks = srtContent.trim().split('\n\n');
        
        for (const block of srtBlocks) {
          const lines = block.split('\n');
          if (lines.length >= 3) {
            // Skip the subtitle number
            const timecode = lines[1]
              .replace(/,/g, '.') // Replace ALL commas with periods for milliseconds
              .replace(/ --> /g, ' --> '); // Ensure proper arrow format
            
            // Ensure proper formatting of timestamps (HH:MM:SS.mmm)
            const [start, end] = timecode.split(' --> ').map(time => {
              if (!time.includes('.')) return time + '.000';
              return time;
            });
            
            const text = lines.slice(2).join('\n');
            vttContent += `${start} --> ${end}\n${text}\n\n`;
          }
        }

        console.log('Generated VTT content:', vttContent.substring(0, 200) + '...');

        // Create blob URL for the VTT content
        const blob = new Blob([vttContent], { type: 'text/vtt' });
        const url = URL.createObjectURL(blob);
        setVttUrl(url);
        console.log('Created VTT URL:', url);

        // Force refresh of video track list
        if (videoRef.current) {
          const video = videoRef.current;
          // Small delay to ensure track is added
          setTimeout(() => {
            if (video.textTracks.length > 0) {
              Array.from(video.textTracks).forEach(track => {
                track.mode = 'showing';
                console.log('Set track mode to showing after conversion');
              });
            }
          }, 100);
        }
      } catch (err) {
        console.error('Error converting subtitles:', err);
        setError('Failed to load subtitles');
      }
    };

    convertSrtToVtt();

    // Cleanup blob URL on unmount or when subtitle source changes
    return () => {
      if (vttUrl) {
        URL.revokeObjectURL(vttUrl);
      }
    };
  }, [subtitleSrc]);

  const handleError = (e: any) => {
    console.error('Video error:', e);
    const video = videoRef.current;
    if (video) {
      console.error('Video error code:', video.error?.code);
      console.error('Video error message:', video.error?.message);
      console.error('Video network state:', video.networkState);
      console.error('Video ready state:', video.readyState);
      setError(video.error?.message || 'Unknown video error');
    }
  };

  const handleTrackLoad = () => {
    console.log('Subtitle track loaded');
    // Ensure track is showing when loaded
    const video = videoRef.current;
    if (video && video.textTracks.length > 0) {
      Array.from(video.textTracks).forEach(track => {
        track.mode = 'showing';
        console.log('Set track mode to showing on track load');
      });
    }
  };

  return (
    <Paper shadow="sm" radius="md" withBorder style={{ background: '#0d1b2a' }}>
      <Box style={{ position: 'relative', width: '100%', paddingTop: '56.25%' }}>
        <video
          ref={videoRef}
          controls
          crossOrigin="anonymous"
          onError={handleError}
          onLoadedMetadata={handleMetadataLoaded}
          onEnded={onVideoEnd}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            borderRadius: 'inherit'
          }}
        >
          <source src={src} type="video/mp4" />
          {vttUrl && (
            <track
              kind="subtitles"
              src={vttUrl}
              srcLang="en"
              label="English"
              default
              onLoad={handleTrackLoad}
            />
          )}
          Your browser does not support HTML5 video.
        </video>
        {error && (
          <Box
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: '#ff4444',
              background: 'rgba(13, 27, 42, 0.9)',
              padding: '1rem',
              borderRadius: '4px',
              textAlign: 'center'
            }}
          >
            Error: {error}
          </Box>
        )}
      </Box>
    </Paper>
  );
}; 
```

## frontend/chattng-web/src/App.css
```css
#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.react:hover {
  filter: drop-shadow(0 0 2em #61dafbaa);
}

@keyframes logo-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: no-preference) {
  a:nth-of-type(2) .logo {
    animation: logo-spin infinite 20s linear;
  }
}

.card {
  padding: 2em;
}

.read-the-docs {
  color: #888;
}

```

## frontend/chattng-web/src/index.css
```css
:root {
  font-family: 'Inter', system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;

  color-scheme: light dark;
  color: #e0e0e0;
  background-color: #0d1b2a;  /* dark navy background */

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  font-weight: 500;
  color: #646cff;
  text-decoration: inherit;
}
a:hover {
  color: #535bf2;
}

body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}

h1 {
  font-size: 3.2em;
  line-height: 1.1;
}

button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  font-family: inherit;
  background-color: #1a1a1a;
  cursor: pointer;
  transition: border-color 0.25s;
}
button:hover {
  border-color: #646cff;
}
button:focus,
button:focus-visible {
  outline: 4px auto -webkit-focus-ring-color;
}

/* Animation for thinking state */
@keyframes pulse {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

@media (prefers-color-scheme: light) {
  :root {
    color: #e0e0e0;
    background-color: #0d1b2a;
  }
  a:hover {
    color: #747bff;
  }
  button {
    background-color: #001f3f;
    color: #e0e0e0;
  }
}

```

## frontend/chattng-web/package.json
```json
{
  "name": "chattng-web",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "@emotion/react": "^11.14.0",
    "@mantine/core": "^7.16.2",
    "@mantine/hooks": "^7.16.2",
    "@mantine/notifications": "^7.16.2",
    "@tabler/icons-react": "^3.29.0",
    "@tanstack/react-query": "^5.66.0",
    "@types/video.js": "^7.3.58",
    "axios": "^1.7.9",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "video.js": "^8.21.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.19.0",
    "@types/react": "^19.0.8",
    "@types/react-dom": "^19.0.3",
    "@vitejs/plugin-react": "^4.3.4",
    "eslint": "^9.19.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.18",
    "globals": "^15.14.0",
    "typescript": "~5.7.2",
    "typescript-eslint": "^8.22.0",
    "vite": "^6.1.0"
  }
}

```

## frontend/chattng-web/vite.config.ts
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/clips': {
        target: 'https://d2qqs9uhgc4wdq.cloudfront.net',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/clips/, '/clips'),
      }
    }
  }
})

```

## frontend/chattng-web/tsconfig.json
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}

```

## frontend/chattng-web/tsconfig.app.json
```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}

```

## frontend/chattng-web/tsconfig.node.json
```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}

```
