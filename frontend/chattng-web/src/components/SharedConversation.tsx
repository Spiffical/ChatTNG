import { Stack, Box, Image, Loader } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { ChatMessage } from './ChatMessage';
import axios from 'axios';
import { useParams } from 'react-router-dom';

interface ClipMetadata {
  clip_path: string;
  start_time: number;
  end_time: number;
  character?: string;
  episode?: string;
  season?: number;
  confidence?: number;
}

interface Message {
  message: string;
  response: string;
  timestamp: number;
  clip_metadata?: ClipMetadata;
}

const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api`;
const CLOUDFRONT_DOMAIN = 'https://d2qqs9uhgc4wdq.cloudfront.net';

const getClipUrl = (clipPath: string) => {
  const path = clipPath.replace('data/processed/clips/', '');
  return `${CLOUDFRONT_DOMAIN}/clips/${path}`;
};

const getSubtitleUrl = (clipPath: string) => {
  const path = clipPath.replace('data/processed/clips/', '');
  const subtitlePath = path.split('.').slice(0, -1).join('.') + '.srt';
  return `${CLOUDFRONT_DOMAIN}/clips/${subtitlePath}`;
};

export const SharedConversation = () => {
  const { shareId } = useParams();

  const { data: conversation, isLoading, error } = useQuery({
    queryKey: ['shared-conversation', shareId],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/chat/share/${shareId}`);
      console.log('Shared conversation data:', response.data); // Debug log
      return response.data;
    }
  });

  if (isLoading) {
    return (
      <Box style={{ 
        width: '100vw', 
        height: '100vh', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        background: '#001f3f'
      }}>
        <Loader color="blue" size="xl" />
      </Box>
    );
  }

  if (error) {
    notifications.show({
      title: 'Error',
      message: 'This conversation has expired or does not exist.',
      color: 'red'
    });
    return (
      <Box style={{ 
        width: '100vw', 
        height: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center',
        background: '#001f3f',
        color: '#fff',
        gap: '1rem'
      }}>
        <h2>Conversation Not Found</h2>
        <p>This shared conversation has expired or does not exist.</p>
      </Box>
    );
  }

  return (
    <Box 
      style={{ 
        width: '100vw', 
        height: '100vh',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: window.innerWidth <= 768 ? '0.5rem' : '1rem',
        position: 'relative',
        zIndex: 1,
        overflow: 'hidden'
      }}
    >
      <Box 
        style={{ 
          width: '100%', 
          maxWidth: '1000px',
          height: '90vh',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          marginTop: window.innerWidth <= 768 ? '0.5rem' : '1rem'
        }}
      >
        {/* Header */}
        <Box 
          p="lg" 
          style={{ 
            background: 'rgba(0, 31, 63, 0.6)',
            borderRadius: window.innerWidth <= 768 ? '15px' : '20px',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
            height: window.innerWidth <= 768 ? '80px' : '100px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            marginBottom: window.innerWidth <= 768 ? '1rem' : '2rem',
            position: 'relative',
            zIndex: 2,
            marginTop: window.innerWidth <= 768 ? '15px' : '30px'
          }}
        >
          <Image
            src="/images/chatTNGlogo.png"
            alt="ChatTNG Logo"
            style={{
              height: window.innerWidth <= 768 ? '100px' : '140px',
              width: 'auto',
              objectFit: 'contain',
              filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))',
              position: 'absolute',
              top: window.innerWidth <= 768 ? '-30px' : '-40px'
            }}
          />
        </Box>

        {/* Messages */}
        <Box
          style={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            marginBottom: '2rem',
            paddingRight: '4px'
          }}
        >
          <Stack gap="xl" p="xl" style={{ padding: window.innerWidth <= 768 ? '0 1rem' : '0 1.5rem' }}>
            {conversation?.messages.map((message: Message, index: number) => (
              <>
                {message.message && (
                  <ChatMessage
                    key={`user-${index}`}
                    role="user"
                    content={message.message}
                  />
                )}
                {message.response && message.clip_metadata && (
                  <ChatMessage
                    key={`assistant-${index}`}
                    role="assistant"
                    content={message.response}
                    clipUrl={getClipUrl(message.clip_metadata.clip_path)}
                    subtitleUrl={getSubtitleUrl(message.clip_metadata.clip_path)}
                    clipMetadata={message.clip_metadata}
                  />
                )}
              </>
            ))}
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}; 