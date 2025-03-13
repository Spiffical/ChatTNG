import { colors, commonStyles, breakpoints } from './common';

export const styles = {
  // Loading container
  loadingContainer: {
    width: '100vw',
    height: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: colors.background
  },
  
  // Error container
  errorContainer: {
    width: '100vw',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    justifyContent: 'center',
    alignItems: 'center',
    background: colors.background,
    color: colors.text.light,
    gap: '1rem',
    padding: '2rem'
  },
  
  // Error details
  errorDetails: {
    maxWidth: '800px',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    padding: '1rem',
    borderRadius: '5px',
    marginTop: '1rem',
    textAlign: 'left' as const,
    fontFamily: 'monospace',
    fontSize: '14px',
    whiteSpace: 'pre-wrap' as const,
    overflow: 'auto' as const,
    maxHeight: '200px'
  },
  
  // Error list
  errorList: {
    textAlign: 'left' as const,
    maxWidth: '600px'
  },
  
  // Button container
  buttonContainer: {
    marginTop: '2rem',
    display: 'flex',
    gap: '1rem'
  },
  
  // Primary button
  primaryButton: {
    padding: '10px 20px',
    backgroundColor: colors.primary,
    color: colors.text.light,
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    fontSize: '16px'
  },
  
  // Secondary button
  secondaryButton: {
    padding: '10px 20px',
    backgroundColor: '#333',
    color: colors.text.light,
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    fontSize: '16px'
  },
  
  // Main container
  mainContainer: {
    width: '100vw',
    height: '100vh',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    padding: window.innerWidth <= breakpoints.mobile ? '0.5rem' : '1rem',
    position: 'relative' as const,
    zIndex: 1,
    overflow: 'hidden' as const
  },
  
  // Chat container
  chatContainer: {
    width: '100%',
    maxWidth: '1000px',
    height: '90vh',
    display: 'flex',
    flexDirection: 'column' as const,
    position: 'relative' as const,
    marginTop: window.innerWidth <= breakpoints.mobile ? '0.5rem' : '1rem'
  },
  
  // Header
  header: {
    ...commonStyles.card,
    height: window.innerWidth <= breakpoints.mobile ? '80px' : '100px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: window.innerWidth <= breakpoints.mobile ? '1rem' : '2rem',
    position: 'relative' as const,
    zIndex: 2,
    marginTop: window.innerWidth <= breakpoints.mobile ? '15px' : '30px'
  },
  
  // Logo
  logo: {
    height: window.innerWidth <= breakpoints.mobile ? '100px' : '140px',
    width: 'auto',
    objectFit: 'contain' as const,
    filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))',
    position: 'absolute' as const,
    top: window.innerWidth <= breakpoints.mobile ? '-30px' : '-40px'
  },
  
  // Messages area
  messagesArea: {
    flex: 1,
    overflowY: 'auto' as const,
    overflowX: 'hidden' as const,
    marginBottom: '2rem',
    paddingRight: '4px'
  },
  
  // Messages stack
  messagesStack: {
    padding: window.innerWidth <= breakpoints.mobile ? '0 1rem' : '0 1.5rem'
  }
}; 