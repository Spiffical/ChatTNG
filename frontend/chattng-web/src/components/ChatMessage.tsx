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

  // Add these debug logs
  console.log('ChatMessage props:', { role, content, clipUrl, subtitleUrl, isPending });
  console.log('isAssistant:', isAssistant);

  // Add this console.log to debug
  console.log('Message:', { role, isAssistant, content });

  const getProxiedUrl = (url: string | undefined) => {
    if (!url) return undefined;
    // Return the full URL without modification
    return url;
  };

  // Render thinking state for assistant
  if (isPending && isAssistant) {
    return (
      <Group 
        align="flex-start" 
        gap="md" 
        wrap="nowrap"
        justify="flex-start"
        style={{ 
          width: '100%',
          flexDirection: 'row'
        }}
      >
        <Avatar
          radius="xl"
          size="md"
          style={{
            background: 'transparent',
            boxShadow: 'none',
            border: 'none'
          }}
        >
          <IconRobot size={20} style={{ color: 'white' }} />
        </Avatar>
        <Box style={{ maxWidth: 'min(600px, 75%)' }}>
          <Paper
            shadow="sm"
            radius="lg"
            p="md"
            style={{
              background: 'transparent',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '1rem 1.5rem',
              minWidth: '80px',
              minHeight: '45px',
              border: 'none',
              boxShadow: 'none'
            }}
          >
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <style>
              {`
                .typing-indicator {
                  display: flex;
                  gap: 6px;
                  padding: 0.5rem;
                  margin: 0 0.5rem;
                }
                
                .typing-indicator span {
                  width: 8px;
                  height: 8px;
                  background-color: #008cff;
                  border-radius: 50%;
                  animation: bounce 1.4s infinite ease-in-out;
                }
                
                .typing-indicator span:nth-child(1) {
                  animation-delay: -0.32s;
                }
                
                .typing-indicator span:nth-child(2) {
                  animation-delay: -0.16s;
                }
                
                @keyframes bounce {
                  0%, 80%, 100% { 
                    transform: translateY(0);
                  }
                  40% { 
                    transform: translateY(-6px);
                  }
                }
              `}
            </style>
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
      style={{ 
        width: '100%',
        padding: '0',
        display: 'flex',
        flexDirection: isAssistant ? 'row' : 'row-reverse',
        position: 'relative',
        margin: '0 0.5rem'
      }}
    >
      <Avatar
        radius="xl"
        size="md"
        style={{
          background: 'transparent',
          boxShadow: 'none',
          flex: '0 0 auto',
          position: 'relative',
          zIndex: 1,
          border: 'none',
          margin: '0'
        }}
      >
        {isAssistant ? <IconRobot size={20} style={{ color: 'white' }} /> : <IconUser size={20} />}
      </Avatar>

      <Box style={{ 
        maxWidth: isAssistant ? 'min(600px, 65%)' : '280px',
        width: '100%',
        display: 'flex',
        justifyContent: isAssistant ? 'flex-start' : 'flex-end',
        flex: '1 1 auto',
        margin: '0',
        position: 'relative'
      }}>
        <Stack 
          gap="xs" 
          style={{ 
            width: isAssistant ? '100%' : 'auto',
            alignItems: isAssistant ? 'flex-start' : 'flex-end',
            minWidth: '150px',
            margin: '0'
          }}
        >
          {isAssistant && clipUrl ? (
            <Box style={{ width: '100%', background: 'transparent' }}>
              <Paper
                radius="md"
                style={{
                  overflow: 'hidden',
                  border: 'none',
                  background: 'transparent',
                  boxShadow: 'none'
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
                  <Box
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '1rem',
                      gap: '0.5rem',
                      background: 'transparent'
                    }}
                  >
                    <Loader size="xs" color="white" variant="dots" className="thinking-dots" />
                    <Text size="sm" c="dimmed">Loading clip...</Text>
                  </Box>
                )}
              </Paper>
              {videoEnded && (
                <Text
                  size="sm"
                  mt="md"
                  style={{
                    fontSize: '0.9rem',
                    marginTop: '0.75rem',
                    marginBottom: '1rem',
                    color: '#e0e0e0',
                    padding: '0.75rem 1rem',
                    background: 'transparent',
                    borderRadius: '8px',
                  }}
                >
                  {content}
                </Text>
              )}
              {clipMetadata && (
                <Text
                  size="sm"
                  c="dimmed"
                  mt="xs"
                  mb="md"
                  style={{
                    fontSize: '0.85rem',
                    color: 'rgba(224, 224, 224, 0.7)',
                  }}
                >
                  Season {clipMetadata.season} Episode {clipMetadata.episode}
                  {clipMetadata.character && ` - ${clipMetadata.character}`}
                </Text>
              )}
            </Box>
          ) : (
            <Paper
              shadow="sm"
              radius="lg"
              style={{
                wordBreak: 'break-word',
                background: isAssistant ? 'transparent' : '#008cff',
                border: 'none',
                borderRadius: '16px',
                boxShadow: isAssistant ? 'none' : '0 2px 8px rgba(0, 0, 0, 0.1)',
                maxWidth: '100%',
                alignSelf: isAssistant ? 'flex-start' : 'flex-end',
                padding: '1rem 1.5rem'
              }}
            >
              <Text
                c={isAssistant ? '#e0e0e0' : 'white'}
                style={{ 
                  whiteSpace: 'pre-wrap', 
                  fontSize: '1rem',
                  lineHeight: '1.5'
                }}
              >
                {content}
              </Text>
            </Paper>
          )}
        </Stack>
      </Box>
    </Group>
  );
}; 