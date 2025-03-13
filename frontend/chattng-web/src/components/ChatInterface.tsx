import { useState, useEffect, useRef } from 'react';
import { Stack, Box, ActionIcon, Image, Popover, Text, Button } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { IconShare2, IconLink, IconHeart } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import axios from 'axios';
import { ChatMessage } from './ChatMessage';
import { styles, textareaCSS } from '../styles/ChatInterfaceStyles';
import { Message } from '../types/chat';

// Constants
const API_BASE_URL = typeof window !== 'undefined' 
  ? (window.__NEXT_DATA__?.props?.pageProps?.apiUrl || import.meta.env.VITE_API_URL || '/api')
  : '/api';

// Debug logging
if (typeof window !== 'undefined') {
  console.log('API Base URL:', API_BASE_URL);
  console.log('Next Data API URL:', window.__NEXT_DATA__?.props?.pageProps?.apiUrl);
  console.log('Vite API URL:', import.meta.env.VITE_API_URL);
}

export const ChatInterface = () => {
  // State
  const [input, setInput] = useState('');
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const [shareUrl, setShareUrl] = useState('');
  const [shareStep, setShareStep] = useState<'confirm' | 'url'>('confirm');
  const [isCopied, setIsCopied] = useState(false);
  const [audioInitialized, setAudioInitialized] = useState(false);
  const [isMobile] = useState(window.innerWidth <= 768);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [contactOpened, { close: closeContact, open: openContact }] = useDisclosure(false);
  const [isContactHovered, setIsContactHovered] = useState(false);

  // Hooks
  const [opened, { close, open }] = useDisclosure(false);

  // Detect Firefox
  const isFirefox = typeof navigator !== 'undefined' && navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
  
  // Check if Visual Viewport API is available
  const hasVisualViewport = typeof window !== 'undefined' && 'visualViewport' in window;

  // Add touch event handling
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      const preventTouchPropagation = (e: TouchEvent) => {
        e.stopPropagation();
      };
      
      textarea.addEventListener('touchstart', preventTouchPropagation, { passive: false });
      textarea.addEventListener('touchmove', preventTouchPropagation, { passive: false });
      
      return () => {
        textarea.removeEventListener('touchstart', preventTouchPropagation);
        textarea.removeEventListener('touchmove', preventTouchPropagation);
      };
    }
  }, []);

  // Handle input focus for Firefox mobile
  const handleInputFocus = () => {
    if (isFirefox && isMobile) {
      // Firefox mobile keyboard handling is now done in ChatInterfaceStyles.ts
      // with direct style manipulation
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  // Handle input blur for Firefox mobile
  const handleInputBlur = () => {
    // Firefox mobile keyboard handling is now done in ChatInterfaceStyles.ts
    // Add a small delay to allow button clicks to process before resetting position
    if (isFirefox && isMobile && !hasVisualViewport) {
      // Small delay to allow submit button click to be processed
      setTimeout(() => {
        // Only reset if we're not in the middle of submitting
        if (!sendMessage.isPending) {
          // Force the input area to return to the bottom
          const inputArea = document.querySelector('.input-area') as HTMLElement;
          if (inputArea) {
            inputArea.style.position = 'fixed';
            inputArea.style.bottom = '0';
            inputArea.style.top = 'auto';
            
            // Reset chat messages container
            const chatMessages = document.querySelector('#chat-messages') as HTMLElement;
            if (chatMessages) {
              chatMessages.style.paddingBottom = 'calc(140px + env(safe-area-inset-bottom))';
            }
            
            // Force scroll to show the last message
            setTimeout(() => {
              if (messagesEndRef.current) {
                messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
              }
            }, 150);
          }
        }
      }, 150);
    }
  };

  // Scroll to last message function
  const scrollToLastMessage = () => {
    const messageStack = document.querySelector('.message-stack');
    if (messageStack) {
      const lastMessage = messageStack.lastElementChild;
      if (lastMessage) {
        lastMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  // Handle video load
  const handleVideoLoad = (containerElement: HTMLElement) => {
    containerElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (isMobile && document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  };

  // Handle video end
  const handleVideoEnd = () => {
    console.log('Video ended in ChatInterface, isMobile:', isMobile);
    if (!isMobile) {
      // Focus the input immediately and also after a short delay to ensure it works
      const focusInput = () => {
        const inputElement = document.querySelector('.chat-input') as HTMLElement;
        if (inputElement) {
          console.log('Focusing input element');
          inputElement.focus();
          // On desktop browsers, also set the cursor to the end of the input
          if (inputElement instanceof HTMLInputElement || inputElement instanceof HTMLTextAreaElement) {
            const length = inputElement.value.length;
            inputElement.setSelectionRange(length, length);
          }
        } else {
          console.log('Input element not found');
        }
      };

      // Try to focus immediately
      focusInput();
      
      // And also after a short delay to ensure it works
      setTimeout(focusInput, 100);
    } else {
      // On mobile, explicitly blur any focused element to ensure keyboard stays hidden
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
    }
  };

  // Replace scrollToBottom with scrollToLastMessage in useEffect
  useEffect(() => {
    scrollToLastMessage();
  }, [localMessages]);

  // Add event listener for video loaded events
  useEffect(() => {
    const handleVideoLoaded = (event: Event) => {
      console.log('Video loaded event received');
      
      // Check if this is a custom event with preventScroll flag
      const customEvent = event as CustomEvent;
      const preventScroll = customEvent.detail?.preventScroll;
      const videoElement = customEvent.detail?.videoElement;
      
      // For Firefox mobile, we need special handling
      if (isFirefox && isMobile) {
        // If preventScroll flag is set, don't do any automatic scrolling
        if (preventScroll) {
          console.log('Preventing automatic scroll for Firefox mobile');
          
          // Only ensure the video is visible without scrolling to top
          if (videoElement) {
            setTimeout(() => {
              videoElement.scrollIntoView({ behavior: 'auto', block: 'center' });
            }, 100);
          }
          return;
        }
        
        // First immediate scroll to get close to the right position
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
        }
        
        // Then do a series of delayed scrolls to ensure everything is visible
        setTimeout(() => {
          // Find the last video element
          const lastVideo = document.querySelector('.video-container:last-of-type video');
          if (lastVideo) {
            // Ensure it's visible
            lastVideo.scrollIntoView({ behavior: 'auto', block: 'center' });
            
            // After video is in view, scroll to show any content below it
            setTimeout(() => {
              if (messagesEndRef.current) {
                messagesEndRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
              }
              
              // Final scroll to ensure everything is visible
              setTimeout(() => {
                if (hasVisualViewport) {
                  // Use Visual Viewport API for more accurate positioning
                  const inputArea = document.querySelector('.input-area') as HTMLElement;
                  const isKeyboardVisible = inputArea && inputArea.style.position === 'absolute';
                  
                  if (isKeyboardVisible) {
                    // If keyboard is visible, don't use window.scrollTo as it can cause scrolling to top
                    // Instead, directly scroll to the last video or message
                    if (lastVideo) {
                      lastVideo.scrollIntoView({ behavior: 'auto', block: 'center' });
                    } else if (messagesEndRef.current) {
                      messagesEndRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
                    }
                  } else {
                    // If keyboard is not visible, just scroll to bottom
                    if (messagesEndRef.current) {
                      messagesEndRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
                    }
                  }
                } else {
                  // Fallback for browsers without Visual Viewport API
                  if (messagesEndRef.current) {
                    messagesEndRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
                  }
                }
              }, 100);
            }, 200);
          } else {
            // If no video found, just scroll to bottom
            scrollToLastMessage();
          }
        }, 100);
      } else {
        // For other browsers, use the standard scrollToLastMessage
        setTimeout(() => {
          scrollToLastMessage();
        }, 100);
      }
    };

    document.addEventListener('videoLoaded', handleVideoLoaded);
    
    return () => {
      document.removeEventListener('videoLoaded', handleVideoLoaded);
    };
  }, []);

  // Additional effect to ensure videos are visible when loaded
  useEffect(() => {
    const handleVideoLoad = () => {
      if (isMobile) {
        // When a video loads, ensure it's visible above the input bar
        setTimeout(scrollToLastMessage, 300);
      }
    };

    // Listen for video load events
    document.addEventListener('videoLoaded', handleVideoLoad);
    
    return () => {
      document.removeEventListener('videoLoaded', handleVideoLoad);
    };
  }, [isMobile]);

  // Effect to add document click listener to close popover
  useEffect(() => {
    if (opened) {
      const handleDocumentClick = (e: MouseEvent) => {
        // Check if click is outside the popover
        const popoverElement = document.querySelector('.mantine-Popover-dropdown');
        const shareButton = document.querySelector('.share-button');
        
        if (popoverElement && shareButton) {
          if (!popoverElement.contains(e.target as Node) && 
              !shareButton.contains(e.target as Node)) {
            close();
          }
        }
      };
      
      // Add the event listener
      document.addEventListener('click', handleDocumentClick);
      
      // Clean up
      return () => {
        document.removeEventListener('click', handleDocumentClick);
      };
    }
  }, [opened, close]);

  // Effect to check for tryShare parameter in URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tryShareId = params.get('tryShare');
    
    if (tryShareId) {
      const directShareUrl = `${window.location.origin}/share/${tryShareId}`;
      notifications.show({
        title: 'Shared Conversation',
        message: (
          <div>
            <p>We detected you were trying to view a shared conversation.</p>
            <p>
              <a href={directShareUrl} style={{ color: 'white', textDecoration: 'underline' }} target="_blank" rel="noopener noreferrer">
                Click here to open it in a new tab
              </a>
            </p>
          </div>
        ),
        color: 'blue',
        autoClose: false
      });
      
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Reset copy state when popover closes
  useEffect(() => {
    if (!opened) {
      setIsCopied(false);
    }
  }, [opened]);

  // Share mutation
  const shareMutation = useMutation({
    mutationFn: async () => {
      if (localMessages.length === 0) {
        throw new Error('No messages to share');
      }
      const response = await axios.post(`${API_BASE_URL}/api/chat/share`, {
        messages: localMessages,
        session_id: 'default',
        expire_days: 7
      });
      const cleanId = response.data.share_url.replace(/^\/?(share\/)?/, '').replace(/\/$/, '');
      const shareUrl = `${window.location.origin}/share/${cleanId}`;
      return { ...response.data, share_url: shareUrl };
    },
    onSuccess: (data) => {
      setShareUrl(data.share_url);
      setShareStep('url');
    },
    onError: () => {
      notifications.show({
        title: 'Share failed',
        message: 'Failed to generate share link. Please try again.',
        color: 'red'
      });
      close();
    }
  });

  // Send message mutation
  const sendMessage = useMutation({
    mutationFn: async ({ content }: { content: string }) => {
      const filteredHistory = localMessages.filter(msg => !msg.isPending);
      const response = await axios.post(`${API_BASE_URL}/api/chat/message`, {
        content,
        conversation_history: filteredHistory
      });
      return response.data;
    },
    onSuccess: (data) => {
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
      
      if (data.clip_url && document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
    }
  });

  // Initialize audio for iOS
  const initializeAudioForIOS = () => {
    if (audioInitialized) return;

    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        const audioCtx = new AudioContext();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        gainNode.gain.value = 0;
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.001);
        setAudioInitialized(true);
      }
    } catch (error) {
      console.error('Error initializing audio:', error);
    }
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    initializeAudioForIOS();
    const message = input;
    setInput('');

    const newUserMessage: Message = { role: 'user', content: message };
    const pendingAssistant: Message = { role: 'assistant', content: '', isPending: true };
    const updatedMessages = [...localMessages, newUserMessage, pendingAssistant];
    setLocalMessages(updatedMessages);

    try {
      await sendMessage.mutateAsync({ content: message });
    } catch {
      setLocalMessages(localMessages);
      notifications.show({
        title: 'Error',
        message: 'Failed to send message. Please try again.',
        color: 'red',
      });
    }
  };

  // Effect to handle document clicks for contact popover
  useEffect(() => {
    if (contactOpened) {
      const handleDocumentClick = (e: MouseEvent) => {
        const popoverElement = document.querySelector('.contact-popover');
        const contactButton = document.querySelector('.contact-button');
        
        if (popoverElement && contactButton) {
          if (!popoverElement.contains(e.target as Node) && 
              !contactButton.contains(e.target as Node)) {
            closeContact();
          }
        }
      };
      
      const timer = setTimeout(() => {
        document.addEventListener('click', handleDocumentClick);
      }, 100);
      
      return () => {
        clearTimeout(timer);
        document.removeEventListener('click', handleDocumentClick);
      };
    }
  }, [contactOpened, closeContact]);

  return (
    <Box style={styles.root} className="vh-fix">
      <Box style={styles.mainWrapper}>
        {/* Header */}
        <Box style={styles.header}>
          {/* Contact/Donation Button */}
          <Box style={styles.contactSection}>
            <Box style={styles.contactButtonContainer}>
              <Popover
                width={300}
                position="bottom"
                withArrow
                shadow="md"
                opened={contactOpened}
                onClose={closeContact}
                withinPortal
                zIndex={2000}
                offset={20}
                closeOnClickOutside={true}
                closeOnEscape={true}
                classNames={{ dropdown: 'contact-popover' }}
              >
                <Popover.Target>
                  <ActionIcon
                    variant="filled"
                    size="xl"
                    color="grape"
                    className="contact-button"
                    onClick={(e) => {
                      contactOpened ? closeContact() : openContact();
                      e.stopPropagation();
                    }}
                    onMouseEnter={() => setIsContactHovered(true)}
                    onMouseLeave={() => setIsContactHovered(false)}
                    style={styles.contactButton(isContactHovered)}
                  >
                    <IconHeart size={28} />
                  </ActionIcon>
                </Popover.Target>
                <Popover.Dropdown style={styles.contactDialog}>
                  <Stack gap="xs">
                    <Text size="md" fw={600} style={styles.contactTitle}>Support ChatTNG</Text>
                    <Text size="sm" style={styles.contactDescription}>
                      If you're enjoying ChatTNG and would like to support its development, consider buying me a coffee! Your support helps keep the project alive.
                    </Text>
                    <Box mt="sm">
                      <Button
                        component="a"
                        href="https://buymeacoffee.com/merileo"
                        target="_blank"
                        rel="noopener noreferrer"
                        variant="filled"
                        size="md"
                        color="grape"
                        style={styles.donateButton}
                        leftSection={<IconHeart size={18} />}
                      >
                        Buy Me a Coffee
                      </Button>
                    </Box>
                    <Box mt="xs">
                      <Text size="xs" c="dimmed" ta="center">
                        Contact: spencer.bialek@gmail.com
                      </Text>
                    </Box>
                  </Stack>
                </Popover.Dropdown>
              </Popover>
            </Box>
          </Box>

          {!isMobile && <Box style={{ flex: '1', height: '100%' }} />}
          
          <Box style={styles.logoContainer}>
            <Image
              src="/images/chatTNGlogo.png"
              alt="ChatTNG Logo"
              onError={(event) => {
                const target = event.target as HTMLImageElement;
                const paths = [
                  './images/chatTNGlogo.png', 
                  './public/images/chatTNGlogo.png',
                  '../public/images/chatTNGlogo.png',
                  '../images/chatTNGlogo.png'
                ];
                
                let pathIndex = 0;
                const tryNextPath = () => {
                  if (pathIndex < paths.length) {
                    target.src = paths[pathIndex];
                    pathIndex++;
                  } else {
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
                  }
                };
                
                target.onerror = tryNextPath;
                tryNextPath();
              }}
              style={styles.logoImage}
            />
          </Box>

          <Box style={styles.shareSection}>
            <Box style={styles.shareButtonContainer}>
              <Popover
                width={400}
                position="bottom"
                withArrow
                shadow="md"
                opened={opened}
                onClose={close}
                withinPortal
                zIndex={2000}
                offset={20}
                closeOnClickOutside={true}
                closeOnEscape={true}
              >
                <Popover.Target>
                  <ActionIcon
                    variant="filled"
                    size="xl"
                    color="grape"
                    className="share-button"
                    onClick={(e) => {
                      if (localMessages.length === 0) {
                        notifications.show({
                          title: 'Cannot share',
                          message: 'Start a conversation before sharing.',
                          color: 'yellow'
                        });
                        return;
                      }
                      opened ? close() : open();
                      e.stopPropagation();
                    }}
                    style={styles.shareButton(localMessages.length > 0)}
                  >
                    <IconShare2 size={28} />
                  </ActionIcon>
                </Popover.Target>
                <Popover.Dropdown style={styles.shareDialog}>
                  {shareStep === 'confirm' ? (
                    <Stack gap="xs">
                      <Text size="md" fw={600} style={styles.shareTitle}>Share this conversation</Text>
                      <Text size="sm" style={styles.shareDescription}>
                        This will create a public link that anyone can use to view this conversation (the link will expire after 7 days of last access).
                      </Text>
                      <Box mt="sm" style={styles.shareButtonInPopover}>
                        <Button
                          variant="filled"
                          size="md"
                          color="grape"
                          loading={shareMutation.isPending}
                          onClick={() => shareMutation.mutate()}
                          style={styles.generateShareButton}
                          leftSection={shareMutation.isPending ? null : <IconLink size={18} />}
                        >
                          {shareMutation.isPending ? 'Generating...' : 'Generate Share Link'}
                        </Button>
                      </Box>
                    </Stack>
                  ) : (
                    <Stack gap="xs">
                      <Text size="md" fw={600} style={styles.shareTitle}>Share Link Generated!</Text>
                      <Box style={styles.shareLinkBox}>
                        <Text size="sm">{shareUrl}</Text>
                      </Box>
                      <Box mt="xs" style={styles.shareActionsContainer}>
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
                                autoClose: 2000
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
                          style={styles.shareActionButton(isCopied)}
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
                          style={styles.closeButton}
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
        </Box>

        {/* Messages Area */}
        <Box id="chat-messages" style={styles.messagesContainer}>
          <Stack gap="xl" style={styles.messagesStack} className="message-stack">
            {localMessages.map((message, index) => (
              <ChatMessage
                key={`message-${index}-${message.role}`}
                role={message.role}
                content={message.content}
                clipUrl={message.clip_url}
                subtitleUrl={message.subtitle_url}
                clipMetadata={message.clip_metadata}
                isPending={message.isPending}
                onVideoLoad={handleVideoLoad}
                onVideoEnd={handleVideoEnd}
              />
            ))}
          </Stack>
          <div ref={messagesEndRef} id="messagesEndRef" />
        </Box>

        {/* Input Area */}
        <Box 
          id="input-area"
          className="input-area"
          style={styles.inputArea}
          ref={inputAreaRef}
        >
          <Box style={styles.inputBox}>
            <form onSubmit={handleSubmit} style={{ width: '100%' }}>
              <Box style={styles.inputContainer}>
                <textarea
                  ref={textareaRef}
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
                  className={`chat-input ${isMobile ? 'mobile-input' : ''}`}
                  onFocus={handleInputFocus}
                  onBlur={handleInputBlur}
                  rows={1}
                  style={isMobile ? { resize: 'none', overflow: 'auto' } : {}}
                />
                <style>{textareaCSS}</style>
                <ActionIcon
                  type="submit"
                  variant="subtle"
                  size="lg"
                  disabled={!input.trim() || sendMessage.isPending}
                  loading={sendMessage.isPending}
                  onClick={(e) => {
                    // Prevent default to handle submission manually
                    e.preventDefault();
                    if (input.trim() && !sendMessage.isPending) {
                      // For Firefox mobile, we need to handle submission manually
                      // to ensure it works even when keyboard is dismissed
                      handleSubmit(e);
                    }
                  }}
                  style={{
                    position: 'absolute',
                    right: '8px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: input.trim() ? '#6A0DAD' : 'rgba(255, 255, 255, 0.3)',
                    transition: 'all 0.2s ease-in-out',
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
    </Box>
  );
}; 
