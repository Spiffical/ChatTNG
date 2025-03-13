import { CSSProperties } from 'react';
import { colors, commonStyles, fonts } from './common';

// Common styles for reuse across components
export const getStyles = (isMobile: boolean) => ({
  // Avatar styles
  avatar: {
    background: 'transparent',
    boxShadow: 'none',
    flex: '0 0 auto',
    position: 'relative' as const,
    zIndex: 1,
    border: 'none',
    margin: '0'
  },
  
  // Message container styles
  messageContainer: {
    ...commonStyles.container,
    padding: '0',
    margin: '2rem 0.5rem',
    position: 'relative' as const,
    zIndex: 5,
    display: 'flex',
    width: '100%',
    minWidth: 0,
    overflow: 'hidden'
  },
  
  // Message content box styles
  messageContentBox: (isAssistant: boolean): CSSProperties => ({
    width: '100%',
    display: 'flex',
    justifyContent: isAssistant ? 'flex-start' : 'flex-end',
    flex: '1 1 auto',
    margin: '0',
    position: 'relative',
    maxWidth: isAssistant ? (isMobile ? '100%' : 'min(600px, 100%)') : (isMobile ? '80%' : '280px'),
    minWidth: isMobile ? 0 : (isAssistant ? '400px' : '150px'),
    zIndex: 5,
    alignSelf: isAssistant ? 'flex-start' : 'flex-end',
    overflow: 'hidden'
  }),
  
  // Message stack styles
  messageStack: (isAssistant: boolean): CSSProperties => ({
    width: isAssistant ? '100%' : 'auto',
    alignItems: isAssistant ? 'flex-start' : 'flex-end',
    minWidth: '150px',
    margin: '0',
    gap: '2rem',
    position: 'relative' as const,
    zIndex: 5
  }),
  
  // Video container styles
  videoContainer: {
    width: isMobile ? '90%' : '100%', 
    minWidth: isMobile ? 0 : '400px',
    maxWidth: '100%',
    background: 'transparent', 
    position: 'relative' as const,
    marginTop: '0.75rem',
    marginBottom: '-4px',
    zIndex: 60,
    transform: isMobile ? 'translate3d(0,0,0)' : 'translateZ(0)',
    transformStyle: isMobile ? 'preserve-3d' : undefined,
    backfaceVisibility: isMobile ? 'hidden' : undefined,
    willChange: 'transform',
    ...(isMobile && { minHeight: '40vh' })
  },
  
  // Video paper styles
  videoPaper: {
    overflow: 'hidden',
    border: 'none',
    background: 'transparent',
    boxShadow: 'none',
    position: 'relative' as const,
    zIndex: 15,
    margin: '0',
    minHeight: '56px',
    padding: '0'
  },
  
  // Loading indicator container
  loadingContainer: {
    ...commonStyles.layout.flexCenter,
    padding: '1rem',
    gap: '0.5rem',
    background: 'transparent',
    position: 'absolute' as const,
    bottom: '0',
    left: '0',
    width: '100%',
    zIndex: 20
  },
  
  // Info icon styles
  infoIconContainer: {
    position: 'absolute' as const, 
    top: '10px', 
    right: isMobile ? '50px' : '10px', 
    zIndex: 140
  },
  
  // Info icon button styles
  infoIcon: (isHovered: boolean): CSSProperties => ({
    backgroundColor: isHovered ? colors.primary : colors.darkBlue,
    transform: isHovered ? commonStyles.animation.hover.transform : 'scale(1)',
    border: `2px solid ${colors.border}`,
    boxShadow: `0 2px 8px ${colors.shadow}`,
    width: '36px',
    height: '36px',
    transition: commonStyles.animation.transition
  }),
  
  // Popover dropdown styles
  popoverDropdown: {
    backgroundColor: colors.darkBlue,
    color: colors.text.light,
    border: `1px solid ${colors.border}`,
    boxShadow: `0 8px 24px ${colors.shadow}`,
    padding: '10px',
    width: '180px',
    zIndex: 2000,
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderRadius: '8px',
    position: 'absolute' as const,
    opacity: 1,
    visibility: 'visible' as const
  },
  
  // Text message paper styles
  textMessagePaper: (isAssistant: boolean): CSSProperties => ({
    wordBreak: 'break-word',
    background: isAssistant ? 'transparent' : colors.primary,
    border: 'none',
    borderRadius: '16px',
    boxShadow: isAssistant ? 'none' : `0 2px 8px ${colors.shadow}`,
    maxWidth: '100%',
    alignSelf: isAssistant ? 'flex-start' : 'flex-end',
    padding: isAssistant ? '1rem 1.5rem' : '0.15rem 1.25rem',
    marginTop: 0
  }),
  
  // Text message content styles
  textMessageContent: (isAssistant: boolean): CSSProperties => ({
    ...commonStyles.text.body,
    whiteSpace: 'pre-wrap',
    color: isAssistant ? colors.text.dark : colors.text.light,
    fontFamily: fonts.family.mono
  }),
  
  // Video ended text styles
  videoEndedText: {
    fontSize: fonts.size.small,
    marginTop: '1.5rem',
    color: colors.text.light,
    padding: '1rem 1.25rem',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '16px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    fontFamily: fonts.family.mono
  },
  
  // Typing indicator container
  typingIndicatorContainer: {
    background: 'transparent',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '1rem 1.5rem',
    minWidth: '80px',
    minHeight: '45px',
    border: 'none',
    boxShadow: 'none'
  }
});

// CSS for the typing indicator animation
export const typingIndicatorCSS = `
  .typing-indicator {
    display: flex;
    gap: 6px;
    padding: 0.5rem;
    margin: 0 0.5rem;
  }
  
  .typing-indicator span {
    width: 8px;
    height: 8px;
    background-color: ${colors.primary};
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
`; 