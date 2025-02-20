import { useState, useEffect, useRef } from 'react';
import { Stack, Box, ActionIcon, Image, Popover, Text } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { ChatMessage } from './ChatMessage';
import axios from 'axios';
import { IconShare2 } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isPending?: boolean;
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

// Get the current hostname for API calls
const API_BASE_URL = '/api';

export const ChatInterface = () => {
  const [input, setInput] = useState('');
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [opened, { close, open }] = useDisclosure(false);
  const [shareUrl, setShareUrl] = useState('');
  const [shareStep, setShareStep] = useState<'confirm' | 'url'>('confirm');
  const [isCopied, setIsCopied] = useState(false);

  // Reset copy state when popover closes
  useEffect(() => {
    if (!opened) {
      setIsCopied(false);
    }
  }, [opened]);

  // Uncomment and update share mutation
  const shareMutation = useMutation({
    mutationFn: async () => {
      console.log('shareMutation called');
      if (localMessages.length === 0) {
        throw new Error('No messages to share');
      }
      const response = await axios.post(`${API_BASE_URL}/chat/share`, {
        messages: localMessages,
        session_id: 'default',
        expire_days: 7
      });
      console.log('Share API response:', response.data);
      // Remove any existing /share/ from the response and construct the URL
      const cleanId = response.data.share_url.replace(/^\/?(share\/)?/, '').replace(/\/$/, '');
      const shareUrl = `${window.location.origin}/share/${cleanId}`;
      return { ...response.data, share_url: shareUrl };
    },
    onSuccess: (data) => {
      setShareUrl(data.share_url);
      setShareStep('url');
    },
    onError: (_error) => {
      notifications.show({
        title: 'Share failed',
        message: 'Failed to generate share link. Please try again.',
        color: 'red'
      });
      close();
    }
  });

  // Update the sendMessage mutation to use the correct endpoint
  const sendMessage = useMutation({
    mutationFn: async ({ content }: { content: string }) => {
      const response = await axios.post(
        `${API_BASE_URL}/chat/message`,
        {
          content,
          conversation_history: localMessages
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      console.log('Server response:', data);
      
      // Update local messages to show the response immediately
      const updatedMessages = localMessages.map(msg => {
        if (msg.role === 'assistant' && msg.isPending) {
          return {
            role: 'assistant' as const,
            content: data.text,
            clip_url: data.clip_url,
            subtitle_url: data.subtitle_url,
            clip_metadata: data.clip_metadata,
            isPending: false
          };
        }
        return msg;
      });
      setLocalMessages(updatedMessages);
      
      // Focus input after a short delay to allow video to start playing
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    const scrollArea = document.getElementById('chat-messages');
    if (scrollArea) {
      scrollArea.scrollTop = scrollArea.scrollHeight;
    }
  }, [localMessages]);

  // Update useEffect to only log state changes
  useEffect(() => {
    console.log('Share state changed:', {
      opened,
      shareStep,
      shareUrl,
      localMessages: localMessages.length
    });
  }, [opened, shareStep, shareUrl, localMessages.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const message = input;
    setInput('');

    // Create optimistic messages
    const newUserMessage: Message = { role: 'user', content: message };
    const pendingAssistant: Message = { role: 'assistant', content: '', isPending: true };
    const updatedMessages = [...localMessages, newUserMessage, pendingAssistant];
    setLocalMessages(updatedMessages);

    try {
      await sendMessage.mutateAsync({ content: message });
    } catch (error) {
      // Remove optimistic updates on error
      setLocalMessages(localMessages);
      notifications.show({
        title: 'Error',
        message: 'Failed to send message. Please try again.',
        color: 'red',
      });
    }
  };

  // Use local messages for rendering
  const displayMessages = localMessages;

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
        zIndex: 1
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
        {/* Header - Floating at top */}
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
            marginTop: window.innerWidth <= 768 ? '15px' : '30px',
            padding: '0 2rem'
          }}
        >
          {/* Logo */}
          <Box style={{ position: 'relative', height: '100%', flex: 1, display: 'flex', justifyContent: 'center' }}>
            <Image
              src="/images/chatTNGlogo.png"
              alt="ChatTNG Logo"
              onError={(e) => {
                console.error('Error loading logo:', e);
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                const parent = target.parentElement;
                if (parent) {
                  const fallback = document.createElement('div');
                  fallback.textContent = 'ChatTNG';
                  fallback.style.color = '#fff';
                  fallback.style.fontSize = '2rem';
                  fallback.style.fontWeight = 'bold';
                  parent.appendChild(fallback);
                }
              }}
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

          {/* Share button - Absolute positioned */}
          <Box style={{ position: 'absolute', right: '2rem', zIndex: 1000 }}>
            <Popover
              width={400}
              position="bottom"
              withArrow
              shadow="md"
              opened={opened}
              withinPortal
              zIndex={2000}
              offset={20}
            >
              <Popover.Target>
                <ActionIcon
                  variant="filled"
                  size="xl"
                  color="grape"
                  onClick={() => {
                    console.log('ActionIcon clicked');
                    if (localMessages.length === 0) {
                      notifications.show({
                        title: 'Cannot share',
                        message: 'Start a conversation before sharing.',
                        color: 'yellow'
                      });
                      return;
                    }
                    opened ? close() : open();
                  }}
                  style={{
                    backgroundColor: localMessages.length === 0 ? 'rgba(103, 58, 183, 0.3)' : '#673ab7',
                    color: localMessages.length === 0 ? 'rgba(255, 255, 255, 0.5)' : 'white',
                    borderRadius: '10px',
                    padding: '10px',
                    width: '50px',
                    height: '50px',
                    transition: 'all 0.2s ease',
                    cursor: localMessages.length === 0 ? 'not-allowed' : 'pointer',
                    boxShadow: localMessages.length === 0 ? 'none' : '0 2px 8px rgba(103, 58, 183, 0.3)'
                  }}
                >
                  <IconShare2 size={28} />
                </ActionIcon>
              </Popover.Target>
              <Popover.Dropdown 
                style={{ 
                  backgroundColor: 'rgba(0, 31, 63, 0.95)',
                  color: '#ffffff',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                  padding: '20px',
                  minHeight: '120px',
                  maxWidth: '320px',
                  zIndex: 2000,
                  backdropFilter: 'blur(10px)',
                  WebkitBackdropFilter: 'blur(10px)',
                  borderRadius: '12px',
                  position: 'absolute',
                  opacity: 1,
                  visibility: 'visible'
                }}
              >
                {shareStep === 'confirm' ? (
                  <Stack gap="xs">
                    <Text size="md" fw={600} style={{ color: '#fff' }}>Share this conversation</Text>
                    <Text size="sm" style={{ color: 'rgba(255, 255, 255, 0.7)', lineHeight: 1.4 }}>
                      This will create a public link that anyone can use to view this conversation (the link will expire after 7 days of last access).
                    </Text>
                    <Box mt="sm">
                      <ActionIcon
                        variant="filled"
                        size="lg"
                        color="grape"
                        loading={shareMutation.isPending}
                        onClick={() => shareMutation.mutate()}
                        style={{
                          width: '100%',
                          height: '36px',
                          borderRadius: '6px',
                          backgroundColor: '#673ab7',
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            backgroundColor: '#5e35b1'
                          }
                        }}
                      >
                        Generate Share Link
                      </ActionIcon>
                    </Box>
                  </Stack>
                ) : (
                  <Stack gap="xs">
                    <Text size="md" fw={600} style={{ color: '#fff' }}>Share Link Generated!</Text>
                    <Box
                      style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        padding: '10px',
                        borderRadius: '6px',
                        wordBreak: 'break-all',
                        fontSize: '13px',
                        fontFamily: 'monospace',
                        color: 'rgba(255, 255, 255, 0.9)'
                      }}
                    >
                      <Text size="sm">{shareUrl}</Text>
                    </Box>
                    <Box mt="xs" style={{ display: 'flex', gap: '8px' }}>
                      <ActionIcon
                        variant="filled"
                        size="lg"
                        color="grape"
                        onClick={() => {
                          navigator.clipboard.writeText(shareUrl).then(() => {
                            setIsCopied(true);
                            notifications.show({
                              title: 'Link Copied!',
                              message: 'Share link copied to clipboard',
                              color: 'teal',
                              autoClose: 2000,
                              radius: 'md',
                              withBorder: true,
                              icon: '✓',
                              styles: {
                                root: {
                                  backgroundColor: 'rgba(0, 31, 63, 0.95)',
                                  borderColor: 'rgba(255, 255, 255, 0.2)',
                                  '&::before': { backgroundColor: 'teal' }
                                },
                                title: { color: '#fff' },
                                description: { color: 'rgba(255, 255, 255, 0.7)' },
                                closeButton: {
                                  color: '#fff',
                                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' }
                                }
                              }
                            });
                          }).catch(() => {
                            setIsCopied(false);
                            notifications.show({
                              title: 'Copy Failed',
                              message: 'Failed to copy link. Please try again.',
                              color: 'red'
                            });
                          });
                        }}
                        style={{
                          flex: 1,
                          height: '36px',
                          borderRadius: '6px',
                          backgroundColor: isCopied ? '#2e7d32' : '#673ab7',
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            backgroundColor: isCopied ? '#1b5e20' : '#5e35b1'
                          }
                        }}
                      >
                        {isCopied ? '✓ Copied!' : 'Copy Link'}
                      </ActionIcon>
                      <ActionIcon
                        variant="subtle"
                        size="lg"
                        onClick={() => {
                          setShareStep('confirm');
                          close();
                        }}
                        style={{
                          flex: 1,
                          height: '36px',
                          borderRadius: '6px',
                          color: 'rgba(255, 255, 255, 0.7)',
                          '&:hover': {
                            backgroundColor: 'rgba(255, 255, 255, 0.1)'
                          }
                        }}
                      >
                        Close
                      </ActionIcon>
                    </Box>
                  </Stack>
                )}
              </Popover.Dropdown>
            </Popover>
          </Box>
        </Box>

        {/* Messages Area - Scrollable */}
        <Box
          id="chat-messages"
          style={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            marginBottom: window.innerWidth <= 768 ? '70px' : '90px',
            paddingRight: '4px',
            paddingBottom: '2rem'
          }}
        >
          <Stack gap="xl" p="xl" style={{ padding: window.innerWidth <= 768 ? '0 1rem' : '0 1.5rem' }}>
            {displayMessages.map((message, index) => (
              <ChatMessage
                key={index}
                role={message.role}
                content={message.content}
                clipUrl={message.clip_url}
                subtitleUrl={message.subtitle_url}
                clipMetadata={message.clip_metadata}
                isPending={message.isPending}
              />
            ))}
          </Stack>
        </Box>

        {/* Input Area - Floating at bottom */}
        <Box 
          style={{ 
            background: 'rgba(0, 31, 63, 0.6)',
            padding: window.innerWidth <= 768 ? '1rem' : '1.5rem',
            position: 'absolute',
            bottom: 0,
            left: '50%',
            transform: 'translateX(-50%)',
            width: window.innerWidth <= 768 ? '95%' : '90%',
            maxWidth: '800px',
            borderRadius: window.innerWidth <= 768 ? '15px' : '20px',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 10,
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)'
          }}
        >
          <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: '600px', position: 'relative' }}>
            <Box
              style={{
                position: 'relative',
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '15px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
              }}
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (input.trim() && !sendMessage.isPending) {
                      handleSubmit(e);
                    }
                  }
                }}
                placeholder="Have a conversation with Star Trek: TNG..."
                disabled={sendMessage.isPending}
                rows={1}
                style={{
                  width: '100%',
                  height: '50px',
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  color: '#e0e0e0',
                  fontSize: window.innerWidth <= 768 ? '0.9rem' : '1rem',
                  padding: window.innerWidth <= 768 ? '12px 3rem 12px 1rem' : '15px 3.5rem 15px 1.5rem',
                  resize: 'none',
                  overflowY: 'auto',
                  display: 'block',
                  lineHeight: '20px',
                  wordWrap: 'break-word',
                  whiteSpace: 'pre-wrap',
                  boxSizing: 'border-box',
                }}
                className="chat-input"
              />
              <style>
                {`
                  .chat-input {
                    font-family: inherit;
                  }
                  .chat-input::placeholder {
                    color: rgba(224, 224, 224, 0.5);
                  }
                  .chat-input:focus {
                    outline: none;
                  }
                  .chat-input:focus + div {
                    border-color: #008cff;
                    background-color: rgba(255, 255, 255, 0.1);
                  }
                  .chat-input::-webkit-scrollbar {
                    width: 6px;
                  }
                  .chat-input::-webkit-scrollbar-track {
                    background: transparent;
                  }
                  .chat-input::-webkit-scrollbar-thumb {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-radius: 3px;
                  }
                  .chat-input {
                    scrollbar-width: thin;
                    scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
                  }
                `}
              </style>
              <ActionIcon
                type="submit"
                variant="subtle"
                size="lg"
                disabled={!input.trim() || sendMessage.isPending}
                loading={sendMessage.isPending}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: input.trim() ? '#008cff' : 'rgba(255, 255, 255, 0.3)',
                  transition: 'all 0.2s ease',
                  background: 'none',
                  border: 'none',
                  cursor: input.trim() ? 'pointer' : 'default',
                  zIndex: 2
                }}
              >
                <svg 
                  width="20" 
                  height="20" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <line x1="12" y1="19" x2="12" y2="5" />
                  <polyline points="5 12 12 5 19 12" />
                </svg>
              </ActionIcon>
            </Box>
          </form>
        </Box>
      </Box>
    </Box>
  );
}; 
