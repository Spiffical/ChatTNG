import { useState, useEffect, useRef } from 'react';
import { Paper, Text, Stack, Group, Avatar, Box, Loader, Popover, ActionIcon } from '@mantine/core';
import { VideoPlayer } from './VideoPlayer';
import { IconUser, IconRobot, IconInfoCircle } from '@tabler/icons-react';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import { getStyles, typingIndicatorCSS } from '../styles/ChatMessageStyles';

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
  onVideoLoad?: (containerElement: HTMLElement) => void;
  onVideoEnd?: () => void;
}

export const ChatMessage = ({
  role,
  content,
  clipUrl,
  subtitleUrl,
  clipMetadata,
  isPending,
  onVideoLoad,
  onVideoEnd
}: ChatMessageProps) => {
  const isAssistant = role === 'assistant';
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [videoEnded, setVideoEnded] = useState(false);
  const [opened, { open, close }] = useDisclosure(false);
  const [isHovered, setIsHovered] = useState(false);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const isMobile = useMediaQuery('(max-width: 768px)') ?? false;
  const styles = getStyles(isMobile);

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
  
  // Format timestamp from seconds to MM:SS format
  const formatTimestamp = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Handle mouse enter with delay
  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  // Handle mouse leave with delay
  const handleMouseLeave = () => {
    setIsHovered(false);
  };

  // Effect to handle document clicks for popover fallback
  useEffect(() => {
    // Only add the handler if the popover is open
    if (opened) {
      const handleDocumentClick = (e: MouseEvent) => {
        // Check if the click is outside any popover content
        const isOutsideClick = 
          !(e.target as Element).closest('.mantine-Popover-dropdown') && 
          !(e.target as Element).closest('.mantine-ActionIcon-root');
          
        if (isOutsideClick) {
          close();
        }
      };
      
      // Add the global click handler with a slight delay to avoid conflicts
      const timer = setTimeout(() => {
        document.addEventListener('click', handleDocumentClick);
      }, 100);
      
      // Cleanup
      return () => {
        clearTimeout(timer);
        document.removeEventListener('click', handleDocumentClick);
      };
    }
  }, [opened, close]);

  // Render thinking state for assistant
  if (isPending && isAssistant) {
    return (
      <Group 
        align="flex-start" 
        gap="md" 
        wrap="nowrap"
        justify="flex-start"
        style={{ 
          ...styles.messageContainer,
          flexDirection: 'row'
        }}
      >
        <Avatar
          radius="xl"
          size="md"
          style={styles.avatar}
        >
          <IconRobot size={20} style={{ color: 'white' }} />
        </Avatar>
        <Box style={{ maxWidth: 'min(600px, 75%)' }}>
          <Paper
            shadow="sm"
            radius="lg"
            p="md"
            style={styles.typingIndicatorContainer}
          >
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <style>
              {typingIndicatorCSS}
            </style>
          </Paper>
        </Box>
      </Group>
    );
  }

  return (
    <Group
      align="flex-start"
      gap="2.5rem"
      wrap="nowrap"
      justify={isAssistant ? 'flex-start' : 'flex-end'}
      style={{ 
        ...styles.messageContainer,
        flexDirection: isAssistant ? 'row' : 'row-reverse'
      }}
    >
      <Avatar
        radius="xl"
        size="md"
        style={styles.avatar}
      >
        {isAssistant ? <IconRobot size={20} style={{ color: 'white' }} /> : <IconUser size={20} />}
      </Avatar>

      <Box style={styles.messageContentBox(isAssistant)}>
        <Stack 
          gap="2.5rem" 
          style={styles.messageStack(isAssistant)}
        >
          {isAssistant && clipUrl ? (
            <Box 
              className="video-container"
              style={styles.videoContainer as any}
              onClick={(e) => {
                // Prevent keyboard from appearing when clicking on video container
                if (document.activeElement instanceof HTMLElement) {
                  document.activeElement.blur();
                }
                e.stopPropagation();
              }}
              onTouchStart={(e) => {
                // Prevent keyboard from appearing when touching video container
                if (document.activeElement instanceof HTMLElement) {
                  document.activeElement.blur();
                }
                e.stopPropagation();
              }}
              ref={videoContainerRef}
            >
              <Paper
                radius="md"
                style={styles.videoPaper}
              >
                <VideoPlayer
                  src={getProxiedUrl(clipUrl) || ''}
                  subtitleSrc={getProxiedUrl(subtitleUrl)}
                  autoplay={true}
                  onVideoLoaded={() => {
                    setVideoLoaded(true);
                    if (videoContainerRef.current) {
                      onVideoLoad?.(videoContainerRef.current);
                    }
                  }}
                  onVideoEnd={() => {
                    console.log('Video ended in ChatMessage');
                    setVideoEnded(true);
                    // Ensure we call onVideoEnd synchronously
                    onVideoEnd?.();
                  }}
                />
                {!videoLoaded && (
                  <Box style={styles.loadingContainer}>
                    <Loader size="xs" color="white" variant="dots" className="thinking-dots" />
                    <Text size="sm" c="dimmed">Loading clip...</Text>
                  </Box>
                )}
              </Paper>
              
              {/* Info marker with popover */}
              {clipMetadata && videoLoaded && (
                <div 
                  style={styles.infoIconContainer}
                  onClick={(e) => {
                    // Prevent keyboard from appearing when clicking on info icon
                    if (document.activeElement instanceof HTMLElement) {
                      document.activeElement.blur();
                    }
                    e.stopPropagation();
                  }}
                >
                  <Popover
                    width={300}
                    position="right"
                    withArrow
                    shadow="md"
                    opened={opened}
                    onClose={close}
                    trapFocus={false}
                    closeOnEscape={true}
                    closeOnClickOutside={true}
                    withinPortal
                    zIndex={2000}
                    offset={20}
                  >
                    <Popover.Target>
                      <ActionIcon
                        variant="filled"
                        radius="xl"
                        size="lg"
                        onClick={(e) => {
                          // Prevent keyboard from appearing
                          if (document.activeElement instanceof HTMLElement) {
                            document.activeElement.blur();
                          }
                          
                          console.log('Info icon clicked, current state:', opened);
                          // Toggle popover state
                          opened ? close() : open();
                          e.stopPropagation();
                        }}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                        style={styles.infoIcon(isHovered)}
                      >
                        <IconInfoCircle size={20} />
                      </ActionIcon>
                    </Popover.Target>
                    <Popover.Dropdown
                      onMouseEnter={handleMouseEnter}
                      onMouseLeave={handleMouseLeave}
                      style={styles.popoverDropdown}
                    >
                      <Stack gap="xs">
                        {clipMetadata.season && (
                          <Box>
                            <Text size="xs" fw={500} c="rgba(255, 255, 255, 0.7)">Season: {typeof clipMetadata.season === 'number' ? Math.floor(clipMetadata.season) : parseInt(String(clipMetadata.season), 10)}</Text>
                          </Box>
                        )}
                        
                        {clipMetadata.episode && (
                          <Box>
                            <Text size="xs" fw={500} c="rgba(255, 255, 255, 0.7)">Episode: {typeof clipMetadata.episode === 'number' ? Math.floor(clipMetadata.episode) : parseInt(String(clipMetadata.episode), 10)}</Text>
                          </Box>
                        )}
                        
                        {clipMetadata.character && (
                          <Box>
                            <Text size="xs" fw={500} c="rgba(255, 255, 255, 0.7)">Character: {clipMetadata.character}</Text>
                          </Box>
                        )}
                        
                        {clipMetadata.start_time !== undefined && clipMetadata.end_time !== undefined && (
                          <Box>
                            <Text size="xs" fw={500} c="rgba(255, 255, 255, 0.7)">Time: {formatTimestamp(clipMetadata.start_time)} - {formatTimestamp(clipMetadata.end_time)}</Text>
                          </Box>
                        )}
                      </Stack>
                    </Popover.Dropdown>
                  </Popover>
                </div>
              )}
              
              {videoEnded && (
                <Text
                  size="sm"
                  mt="md"
                  style={styles.videoEndedText}
                >
                  {content}
                </Text>
              )}
            </Box>
          ) : (
            <Paper
              shadow="sm"
              radius="lg"
              style={styles.textMessagePaper(isAssistant)}
            >
              <Text style={styles.textMessageContent(isAssistant)}>
                {content}
              </Text>
            </Paper>
          )}
        </Stack>
      </Box>
    </Group>
  );
}; 