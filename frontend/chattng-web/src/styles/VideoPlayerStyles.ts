import { CSSProperties } from 'react';

export const getStyles = (isMobile: boolean) => ({
  // Main container
  container: {
    background: 'transparent',
    borderRadius: 'md',
    boxShadow: 'none',
    border: 'none',
    position: 'relative' as const,
    zIndex: 100, // Much higher z-index to ensure it's above everything else
    width: '100%',
    minWidth: isMobile ? 0 : '400px',
    maxWidth: '100%',
    minHeight: isMobile ? '40vh' : 'auto',
    overflow: 'hidden',
    marginBottom: 0,
    paddingBottom: 0
  },
  
  // Video wrapper
  videoWrapper: {
    position: 'relative' as const,
    width: '100%',
    minWidth: isMobile ? 0 : '400px',
    maxWidth: '100%',
    paddingTop: '56.25%', // 16:9 aspect ratio
    zIndex: 110, // Higher z-index
    minHeight: isMobile ? '200px' : 'auto',
    overflow: 'hidden',
    background: 'transparent',
    marginBottom: 0,
    paddingBottom: 0
  },
  
  // Video element
  video: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    minWidth: isMobile ? 0 : '400px',
    maxWidth: '100%',
    borderRadius: 'inherit',
    zIndex: 120, // Higher z-index than wrapper
    objectFit: 'contain' as const,
    background: '#000',
    marginBottom: 0,
    paddingBottom: 0
  },
  
  // Error message
  errorMessage: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: '#ff4444',
    background: `rgba(13, 27, 42, 0.9)`,
    padding: '1rem',
    borderRadius: '4px',
    textAlign: 'center' as const,
    maxWidth: '80%',
    zIndex: 130 // Higher z-index than video
  }
}) as Record<string, CSSProperties>; 