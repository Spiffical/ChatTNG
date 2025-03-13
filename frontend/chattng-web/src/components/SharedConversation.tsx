import { Stack, Box, Image, Loader } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { ChatMessage } from './ChatMessage';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { styles } from '../styles/SharedConversationStyles';

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

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const CLOUDFRONT_DOMAIN = import.meta.env.VITE_CLOUDFRONT_DOMAIN || 'd3h9bmq6ehlxbf.cloudfront.net';

// Function to try to detect the correct API port - keeping this for future reference
// but simplifying the implementation
const detectApiPort = () => {
  // If we're on localhost, try both the API_BASE_URL and the same origin
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return [
      API_BASE_URL,
      `${window.location.origin}`
    ];
  }
  
  // For production, just use the configured API URL
  return [API_BASE_URL];
};

const getClipUrl = (clipPath: string) => {
  const path = clipPath.replace('data/processed/clips/', '');
  return `https://${CLOUDFRONT_DOMAIN}/clips/${path}`;
};

const getSubtitleUrl = (clipPath: string) => {
  const path = clipPath.replace('data/processed/clips/', '');
  const subtitlePath = path.split('.').slice(0, -1).join('.') + '.srt';
  return `https://${CLOUDFRONT_DOMAIN}/clips/${subtitlePath}`;
};

export const SharedConversation = () => {
  const { shareId } = useParams();

  // Simplified logging without creating debug element
  useEffect(() => {
    console.log('Loading shared conversation:', {
      shareId,
      origin: window.location.origin
    });
  }, [shareId]);

  const { data: conversation, isLoading, error } = useQuery({
    queryKey: ['shared-conversation', shareId],
    queryFn: async () => {
      try {
        // Try multiple approaches to construct the API URL
        const possibleUrls = [];
        
        // Get possible API base URLs
        const apiBaseUrls = detectApiPort();
        
        // Add all possible full URLs
        for (const baseUrl of apiBaseUrls) {
          possibleUrls.push({
            name: `API URL: ${baseUrl}`,
            url: `${baseUrl}/api/chat/share/${shareId}`
          });
        }
        
        // Also try a relative path as fallback
        possibleUrls.push({
          name: 'Relative path',
          url: `/api/chat/share/${shareId}`
        });
        
        // Try each URL in sequence
        let lastError = null;
        for (const { name, url } of possibleUrls) {
          try {
            console.log(`Attempting to fetch from ${name}: ${url}`);
            const response = await axios.get(url);
            console.log(`Success with ${name}`);
            return response.data;
          } catch (err) {
            console.error(`Failed with ${name}:`, err);
            lastError = err;
          }
        }
        
        // If all attempts failed, throw the last error
        throw lastError || new Error('All API URL attempts failed');
      } catch (err) {
        console.error('Error fetching shared conversation:', err);
        if (axios.isAxiosError(err)) {
          console.error('API Error details:', {
            status: err.response?.status,
            statusText: err.response?.statusText,
            data: err.response?.data,
            config: {
              url: err.config?.url,
              method: err.config?.method,
              baseURL: err.config?.baseURL
            }
          });
        }
        throw err;
      }
    },
    retry: 2, // Retry failed requests up to 2 times
    retryDelay: 1000 // Wait 1 second between retries
  });

  // Store error details for display
  const [errorDetails, setErrorDetails] = useState<string>('');
  
  // Update error details when error changes
  useEffect(() => {
    if (error) {
      let details = 'Unknown error';
      
      if (axios.isAxiosError(error)) {
        if (error.code === 'ERR_NETWORK') {
          details = 'Network error: The API server could not be reached. It may be down or not running on the expected port.';
        } else if (error.response) {
          details = `Server responded with status ${error.response.status}: ${error.response.statusText}`;
        } else {
          details = `Request error: ${error.message}`;
        }
        
        details += `\n\nRequested URL: ${error.config?.url}`;
      } else if (error instanceof Error) {
        details = error.message;
      }
      
      setErrorDetails(details);
      console.error('Error details:', details);
    }
  }, [error]);

  if (isLoading) {
    return (
      <Box style={styles.loadingContainer}>
        <Loader color="blue" size="xl" />
      </Box>
    );
  }

  if (error) {
    notifications.show({
      title: 'Error Loading Conversation',
      message: 'Unable to load the shared conversation. See details below.',
      color: 'red'
    });
    
    // Function to try to fix the URL by redirecting to the main site
    const tryToFixUrl = () => {
      const currentUrl = window.location.href;
      const shareId = currentUrl.split('/').pop();
      const mainSiteUrl = window.location.origin;
      
      // Redirect to the main site with a query parameter
      window.location.href = `${mainSiteUrl}?tryShare=${shareId}`;
    };
    
    return (
      <Box style={styles.errorContainer}>
        <h2>Unable to Load Conversation</h2>
        <p>We couldn't load this shared conversation. This could be due to:</p>
        <ul style={styles.errorList}>
          <li>The conversation link has expired</li>
          <li>The server is currently unavailable</li>
          <li>The conversation ID is invalid or has been deleted</li>
        </ul>
        
        {errorDetails && (
          <div style={styles.errorDetails}>
            <p>{errorDetails}</p>
          </div>
        )}
        
        <div style={styles.buttonContainer}>
          <button 
            onClick={tryToFixUrl}
            style={styles.primaryButton}
          >
            Try to Fix
          </button>
          <button 
            onClick={() => window.location.href = window.location.origin}
            style={styles.secondaryButton}
          >
            Go to Home Page
          </button>
        </div>
      </Box>
    );
  }

  return (
    <Box style={styles.mainContainer}>
      <Box style={styles.chatContainer}>
        {/* Header */}
        <Box p="lg" style={styles.header}>
          <Image
            src="/images/chatTNGlogo.png"
            alt="ChatTNG Logo"
            style={styles.logo}
          />
        </Box>

        {/* Messages */}
        <Box style={styles.messagesArea}>
          <Stack gap="xl" p="xl" style={styles.messagesStack}>
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