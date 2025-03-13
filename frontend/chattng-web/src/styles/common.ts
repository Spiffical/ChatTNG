import { CSSProperties } from 'react';

// Colors used throughout the application
export const colors = {
  background: '#000000',
  darkBlue: '#001F3F',
  primary: '#6A0DAD',
  secondary: '#9B30FF',
  border: 'rgba(255, 255, 255, 0.1)',
  shadow: 'rgba(0, 0, 0, 0.4)',
  text: {
    light: '#FFFFFF',
    dark: '#000000'
  }
};

// Font styles used throughout the application
export const fonts = {
  family: {
    mono: "'Roboto Mono', monospace"
  },
  size: {
    small: '0.875rem',
    body: '1rem',
    heading: '1.5rem'
  }
};

// Breakpoints for responsive design
export const breakpoints = {
  mobile: 768,
  tablet: 1024,
  desktop: 1280
};

// Common animation properties
const animation = {
  transition: 'all 0.2s ease-in-out',
  hover: {
    transform: 'scale(1.05)'
  }
};

// Common layout styles
const layout = {
  flexCenter: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center'
  },
  flexColumn: {
    display: 'flex',
    flexDirection: 'column'
  },
  flexRow: {
    display: 'flex',
    flexDirection: 'row'
  }
};

// Common text styles
const text = {
  body: {
    fontSize: fonts.size.body,
    lineHeight: '1.5',
    color: colors.text.light,
    fontFamily: fonts.family.mono
  },
  heading: {
    fontSize: fonts.size.heading,
    fontWeight: 600,
    color: colors.text.light,
    fontFamily: fonts.family.mono
  },
  small: {
    fontSize: fonts.size.small,
    lineHeight: '1.4',
    color: colors.text.light,
    fontFamily: fonts.family.mono
  }
};

// Common card style
const card: CSSProperties = {
  backgroundColor: 'rgba(0, 31, 63, 0.95)',
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  borderRadius: '20px',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
};

// Common container style
const container: CSSProperties = {
  width: '100%',
  maxWidth: '1200px',
  margin: '0 auto',
  padding: '0 1rem'
};

// Common notification styles
const notification = {
  root: {
    backgroundColor: colors.darkBlue,
    border: `1px solid ${colors.border}`,
    borderRadius: '8px'
  },
  title: {
    color: colors.text.light,
    fontWeight: 600
  },
  description: {
    color: 'rgba(255, 255, 255, 0.7)'
  }
};

// Export all common styles
export const commonStyles = {
  card,
  container,
  layout,
  animation,
  text,
  notification
}; 