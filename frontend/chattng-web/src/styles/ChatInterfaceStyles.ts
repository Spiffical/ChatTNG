// Extend Navigator type for Brave browser detection
declare global {
  interface Navigator {
    brave?: {
      isBrave: () => boolean;
    };
  }
}

import { CSSProperties } from 'react';
import { colors, commonStyles, breakpoints, fonts } from './common';

// Utility function to check if we're on mobile
const isMobileWidth = () => window.innerWidth <= breakpoints.mobile;

// Create a CSS custom property for mobile state
if (typeof window !== 'undefined') {
  // Track keyboard and browser state
  const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
  const isBrave = Boolean(navigator.brave);
  
  // Function to ensure input is visible in Brave
  const ensureInputVisibleInBrave = (inputArea: HTMLElement) => {
    if (!isBrave) return;
    
    // Force the input area to be visible
    inputArea.style.position = 'fixed';
    inputArea.style.bottom = '0';
    inputArea.style.transform = 'translate(-50%, 0)';
    inputArea.style.zIndex = '1000';
    
    // Scroll to make input visible after a short delay
    setTimeout(() => {
      inputArea.scrollIntoView({ behavior: 'auto', block: 'end' });
      // Additional scroll to ensure it's fully visible
      window.scrollTo(0, document.body.scrollHeight);
    }, 50);
  };

  // Function to stabilize video container height during loading
  const stabilizeVideoContainer = (browser: 'brave' | 'firefox') => {
    // Skip if the browser doesn't match or isn't Brave/Firefox
    if (!isBrave && !isFirefox) return;
    if (browser === 'brave' && !isBrave) return;
    if (browser === 'firefox' && !isFirefox) return;

    // Get the latest video container
    const videoContainer = document.querySelector('.video-container:last-of-type') as HTMLDivElement;
    if (!videoContainer) return;

    // Get the video element inside the container
    const videoElement = videoContainer.querySelector('video') as HTMLVideoElement;
    if (!videoElement) return;

    // Create a loading placeholder
    const loadingPlaceholder = document.createElement('div');
    loadingPlaceholder.className = 'loading-placeholder';
    loadingPlaceholder.style.position = 'absolute';
    loadingPlaceholder.style.top = '0';
    loadingPlaceholder.style.left = '0';
    loadingPlaceholder.style.width = '100%';
    loadingPlaceholder.style.height = '100%';
    loadingPlaceholder.style.display = 'flex';
    loadingPlaceholder.style.alignItems = 'center';
    loadingPlaceholder.style.justifyContent = 'center';
    loadingPlaceholder.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    loadingPlaceholder.style.color = 'white';
    loadingPlaceholder.style.fontFamily = fonts.family.mono;
    loadingPlaceholder.style.zIndex = '10';
    loadingPlaceholder.innerHTML = '<span style="font-size: 16px;">Loading...</span>';

    // Add the placeholder to the container
    videoContainer.appendChild(loadingPlaceholder);

    // Hide the video element initially to prevent showing the previous frame
    videoElement.style.visibility = 'hidden';
    videoElement.style.opacity = '0';

    // Set container styles to reserve space with a default 16:9 aspect ratio
    videoContainer.style.position = 'relative';
    videoContainer.style.width = '100%';
    videoContainer.style.paddingTop = '56.25%';

    // Position the video absolutely within the container
    videoElement.style.position = 'absolute';
    videoElement.style.top = '0';
    videoElement.style.left = '0';
    videoElement.style.width = '100%';
    videoElement.style.height = '100%';
    videoElement.style.objectFit = 'contain';
    videoElement.style.transition = 'opacity 0.3s ease-in';

    // Reset the video element to clear any previous content
    const currentSrc = videoElement.src;
    videoElement.src = '';
    videoElement.load();

    // Set the new video source with a unique query parameter to avoid caching
    videoElement.src = `${currentSrc}?t=${Date.now()}`;
    videoElement.load();

    // Adjust the container's aspect ratio based on the video's natural dimensions
    videoElement.addEventListener('loadedmetadata', () => {
      const aspectRatio = (videoElement as HTMLVideoElement & { naturalHeight: number; naturalWidth: number }).naturalHeight / 
                         (videoElement as HTMLVideoElement & { naturalHeight: number; naturalWidth: number }).naturalWidth;
      videoContainer.style.paddingTop = `${aspectRatio * 100}%`;
    }, { once: true });

    // Show the video and remove the placeholder when the new video is ready
    videoElement.addEventListener('loadeddata', () => {
      loadingPlaceholder.remove();
      videoElement.style.visibility = 'visible';
      videoElement.style.opacity = '1';
    }, { once: true });
  };

  const updateMobileState = () => {
    const isMobile = isMobileWidth();
    document.documentElement.style.setProperty('--is-mobile', isMobile ? '1' : '0');
    document.documentElement.style.setProperty('--header-top', isMobile ? '0' : '20px');
    document.documentElement.style.setProperty('--header-left', isMobile ? '0' : 'auto');
    document.documentElement.style.setProperty('--flex-value', isMobile ? '1' : '0');
    document.documentElement.style.setProperty('--justify-content', isMobile ? 'flex-start' : 'center');
    document.documentElement.style.setProperty('--logo-justify', isMobile ? 'flex-start' : 'center');
    document.documentElement.style.setProperty('--is-firefox', isFirefox ? '1' : '0');
    document.documentElement.style.setProperty('--is-brave', isBrave ? '1' : '0');
    // Add specific padding values for mobile and desktop
    document.documentElement.style.setProperty('--messages-top-padding', isMobile ? '1rem' : '1rem');
    document.documentElement.style.setProperty('--messages-margin-top', isMobile ? '20px' : '25px');
    // Add font size variables
    document.documentElement.style.setProperty('--input-font-size', isMobile ? fonts.size.small : fonts.size.body);
    document.documentElement.style.setProperty('--placeholder-font-size', isMobile ? fonts.size.small : fonts.size.body);
    // Add font family variable
    document.documentElement.style.setProperty('--input-font-family', fonts.family.mono);

    // Listen for video will load events to prepare the container
    document.addEventListener('videoWillLoad', () => {
      console.log('Video will load event received');
      
      if (isBrave) {
        stabilizeVideoContainer('brave');
      } else if (isFirefox) {
        stabilizeVideoContainer('firefox');
      }
    });
  };
  
  // Initial setup - ensure this runs immediately
  updateMobileState();
  
  // Setup resize handler with cleanup
  const setupResizeHandler = () => {
    window.addEventListener('resize', updateMobileState);
    return () => {
      window.removeEventListener('resize', updateMobileState);
    };
  };
  
  // Initialize the resize handler
  setupResizeHandler();

  // Add a DOMContentLoaded event to ensure styles are applied after the DOM is fully loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateMobileState);
  } else {
    // DOM is already loaded, run the function
    setTimeout(updateMobileState, 0);
  }
  
  // Handle Firefox and Brave mobile keyboard specifically
  if ((isFirefox || isBrave) && isMobileWidth()) {
    // Add focus/blur handlers for input elements to adjust positioning
    document.addEventListener('DOMContentLoaded', () => {
      // Track keyboard state
      let isKeyboardVisible = false;
      let initialViewportHeight = 0;
      
      // Use Visual Viewport API if available for better keyboard detection
      const hasVisualViewport = typeof window !== 'undefined' && 'visualViewport' in window;
      
      if (hasVisualViewport) {
        console.log('Using Visual Viewport API for mobile keyboard handling');
        
        // Store initial viewport height for comparison
        initialViewportHeight = window.visualViewport?.height || window.innerHeight;
        
        const adjustForVisualViewport = () => {
          const currentHeight = window.visualViewport?.height || 0;
          // If the visual viewport height is significantly smaller than initial height,
          // we can assume the keyboard is visible
          const keyboardVisible = currentHeight < initialViewportHeight * 0.75;
          
          if (keyboardVisible !== isKeyboardVisible) {
            adjustForKeyboard(keyboardVisible);
          }
        };
        
        // Listen for visual viewport resize events
        window.visualViewport?.addEventListener('resize', adjustForVisualViewport);
        
        // Add input event listener for Brave to handle initial keyboard popup
        if (isBrave) {
          document.addEventListener('input', (e) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains('chat-input') || target.classList.contains('mobile-input')) {
              const inputArea = document.querySelector('.input-area') as HTMLElement;
              if (inputArea) {
                ensureInputVisibleInBrave(inputArea);
              }
            }
          }, true);
        }
        
        // Prevent unwanted scrolling to top
        window.visualViewport?.addEventListener('scroll', (e) => {
          if (isKeyboardVisible) {
            e.preventDefault();
            
            if (isBrave) {
              const inputArea = document.querySelector('.input-area') as HTMLElement;
              if (inputArea) {
                ensureInputVisibleInBrave(inputArea);
              }
            } else {
              // Existing code for other browsers
              const lastVideo = document.querySelector('.video-container:last-of-type video');
              const lastMessage = document.querySelector('.messageStack > div:last-child');
              
              if (lastVideo) {
                setTimeout(() => {
                  lastVideo.scrollIntoView({ behavior: 'auto', block: 'center' });
                }, 50);
              } else if (lastMessage) {
                setTimeout(() => {
                  lastMessage.scrollIntoView({ behavior: 'auto', block: 'end' });
                }, 50);
              }
            }
          }
        });
        
        // Initial check
        setTimeout(adjustForVisualViewport, 300);
      }
      
      const adjustForKeyboard = (keyboardVisible: boolean) => {
        // Only process if state is actually changing
        if (isKeyboardVisible === keyboardVisible) return;
        
        isKeyboardVisible = keyboardVisible;
        const inputArea = document.querySelector('.input-area') as HTMLElement;
        const chatMessages = document.querySelector('#chat-messages') as HTMLElement;
        
        if (inputArea) {
          if (keyboardVisible) {
            if (isBrave) {
              // Special handling for Brave's initial keyboard popup
              inputArea.style.position = 'fixed';
              inputArea.style.bottom = '0';
              inputArea.style.transform = 'translate(-50%, 0)';
              inputArea.style.zIndex = '1000';
              
              // Add extra padding to ensure content is visible
              if (chatMessages) {
                chatMessages.style.paddingBottom = '240px';
              }
              
              // Force scroll to make input visible
              setTimeout(() => {
                inputArea.scrollIntoView({ behavior: 'auto', block: 'end' });
                window.scrollTo(0, document.body.scrollHeight);
              }, 50);
            } else {
              // Existing code for other browsers
              inputArea.style.position = 'absolute';
              inputArea.style.bottom = 'auto';
              
              if (hasVisualViewport) {
                // Position the input area just above the keyboard using Visual Viewport
                const visualViewportHeight = window.visualViewport?.height || window.innerHeight;
                const inputHeight = inputArea.offsetHeight || 60;
                const safeAreaInsetBottom = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--safe-area-inset-bottom')) || 0;
                
                // Add extra padding for Firefox and Brave
                const browserPadding = (isFirefox || isBrave) ? 20 : 0;
                inputArea.style.top = `${visualViewportHeight - inputHeight - safeAreaInsetBottom - browserPadding}px`;
                
                // Add specific styles for Firefox and Brave
                if (isFirefox || isBrave) {
                  inputArea.style.transform = 'translateZ(0)';
                  inputArea.style.willChange = 'transform';
                  inputArea.style.zIndex = '1000';
                }
              } else {
                // Fallback to percentage-based positioning with browser-specific adjustments
                const positionPercentage = (isFirefox || isBrave) ? 0.4 : 0.45;
                inputArea.style.top = `${window.innerHeight * positionPercentage}px`;
              }
              
              // Add transition for smoother movement
              inputArea.style.transition = 'top 0.2s ease-out, position 0.2s ease-out';
              inputArea.style.willChange = 'top, position';
              
              // Adjust chat messages container to ensure content is visible
              if (chatMessages) {
                const extraPadding = (isFirefox || isBrave) ? '220px' : '200px';
                chatMessages.style.paddingBottom = extraPadding;
                chatMessages.scrollTop = chatMessages.scrollHeight;
              }
              
              // Scroll to ensure input is visible with a delay for keyboard animation
              setTimeout(() => {
                if (hasVisualViewport) {
                  const lastVideo = document.querySelector('.video-container:last-of-type video');
                  if (lastVideo) {
                    lastVideo.scrollIntoView({ behavior: 'auto', block: 'center' });
                  } else {
                    inputArea.scrollIntoView({ behavior: 'auto', block: 'end' });
                  }
                } else {
                  window.scrollTo(0, document.body.scrollHeight);
                }
              }, isFirefox || isBrave ? 150 : 100);
            }
          } else {
            // Reset position when keyboard is hidden
            inputArea.style.position = 'fixed';
            inputArea.style.bottom = '0';
            inputArea.style.top = 'auto';
            inputArea.style.transform = 'translateX(-50%)';
            
            // Reset chat messages container
            if (chatMessages) {
              chatMessages.style.paddingBottom = 'calc(140px + env(safe-area-inset-bottom))';
            }
            
            // Force scroll to show the last message
            setTimeout(() => {
              const messagesEnd = document.querySelector('#messagesEndRef') as HTMLElement;
              if (messagesEnd) {
                messagesEnd.scrollIntoView({ behavior: 'smooth', block: 'end' });
              } else {
                window.scrollTo(0, document.body.scrollHeight);
              }
            }, isBrave ? 250 : 200);
          }
        }
      };
      
      // Add event listeners to detect keyboard visibility
      document.addEventListener('focus', (e) => {
        const target = e.target as HTMLElement;
        if (target.classList.contains('chat-input') || target.classList.contains('mobile-input')) {
          if (!hasVisualViewport) {
            adjustForKeyboard(true);
          }
        }
      }, true);
      
      document.addEventListener('blur', (e) => {
        const target = e.target as HTMLElement;
        if (target.classList.contains('chat-input') || target.classList.contains('mobile-input')) {
          // Add a small delay to allow button clicks to process
          setTimeout(() => {
            // Check if we're not in the middle of a form submission
            const submitButton = document.querySelector('.input-area button[type="submit"]');
            const isSubmitting = submitButton && submitButton.classList.contains('mantine-Button-loading');
            
            // Check if any input element is still focused
            const anyInputFocused = document.activeElement && 
              (document.activeElement.classList.contains('chat-input') || 
               document.activeElement.classList.contains('mobile-input'));
            
            // Only reset if we're not submitting and no input is focused
            if (!isSubmitting && !anyInputFocused && !hasVisualViewport) {
              adjustForKeyboard(false);
            }
          }, 150);
        }
      }, true);
      
      // Also listen for form submissions to ensure proper handling
      document.addEventListener('submit', (e) => {
        if (e.target && (e.target as HTMLElement).closest('.input-area')) {
          // Keep the keyboard position for a moment to allow submission to complete
          setTimeout(() => {
            adjustForKeyboard(false);
          }, 300);
        }
      });
      
      // Listen for video loaded events to ensure they're visible
      document.addEventListener('videoLoaded', () => {
        console.log('Video loaded event received');
        requestAnimationFrame(() => {
          const messagesEnd = document.querySelector('#messagesEndRef') as HTMLElement;
          if (messagesEnd) {
            messagesEnd.scrollIntoView({ behavior: 'smooth', block: 'end' });
          } else {
            // Fallback: scroll to bottom of document if #messagesEndRef is missing
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
          }
        });
      });
      
      // Add a listener for the visibilitychange event to handle keyboard dismissal
      // when the user switches apps or tabs
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && isKeyboardVisible) {
          // When returning to the app, check if keyboard is still visible
          // If not, reset the input area position
          setTimeout(() => {
            if (hasVisualViewport) {
              const currentHeight = window.visualViewport?.height || 0;
              // If height is close to initial height, keyboard is likely hidden
              if (currentHeight > initialViewportHeight * 0.9) {
                adjustForKeyboard(false);
              }
            } else {
              // Use a heuristic to determine if keyboard is likely hidden
              const viewportHeight = window.innerHeight;
              const documentHeight = document.documentElement.clientHeight;
              
              // If viewport height is close to document height, keyboard is likely hidden
              if (viewportHeight > documentHeight * 0.9) {
                adjustForKeyboard(false);
              }
            }
          }, 300);
        }
      });
    });
  }
}

export const styles = {
  // Root container
  root: {
    width: '100vw',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    background: colors.background,
    overflow: 'hidden',
    paddingTop: 'calc(var(--is-mobile) * 0px + (1 - var(--is-mobile)) * 2rem)',
    position: 'relative'
  } as CSSProperties,

  // Main wrapper
  mainWrapper: {
    width: '100%',
    maxWidth: 'calc(var(--is-mobile) * 100% + (1 - var(--is-mobile)) * 1200px)',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative'
  } as CSSProperties,

  // Header
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    maxWidth: '1200px',
    padding: '0',
    position: 'relative',
    top: 'var(--header-top)',
    left: 'var(--header-left)',
    zIndex: 1000,
    minHeight: 'calc(var(--is-mobile) * 60px + (1 - var(--is-mobile)) * 70px)',
    height: 'calc(var(--is-mobile) * 60px + (1 - var(--is-mobile)) * 100px)',
    borderRadius: 'calc(var(--is-mobile) * 0px + (1 - var(--is-mobile)) * 20px)',
    background: 'rgba(0, 31, 63, 0.95)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    margin: '0 auto'
  } as CSSProperties,

  // Logo section
  logoContainer: {
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    padding: '0',
    pointerEvents: 'none' as const,
    width: 'auto'
  } as CSSProperties,

  logoImage: {
    height: 'calc(var(--is-mobile) * 40px + (1 - var(--is-mobile)) * 140px)',
    objectFit: 'contain' as const,
    margin: '0',
    pointerEvents: 'auto' as const
  },

  // Share button section
  shareSection: {
    display: 'flex',
    flex: '0 0 auto',
    justifyContent: 'flex-end',
    alignItems: 'center',
    height: '100%',
    padding: '0 1rem',
    marginLeft: 'auto'
  } as CSSProperties,

  shareButtonContainer: {
    marginLeft: 'calc(var(--is-mobile) * 0.5rem + (1 - var(--is-mobile)) * 0)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%'
  } as CSSProperties,

  shareButton: (hasMessages: boolean): CSSProperties => ({
    backgroundColor: hasMessages ? colors.secondary : `${colors.secondary}4D`,
    color: hasMessages ? colors.text.light : `${colors.text.light}80`,
    height: '50px',
    width: '50px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: 'auto 0',
    transition: commonStyles.animation.transition,
    cursor: hasMessages ? 'pointer' : 'not-allowed',
    boxShadow: hasMessages ? `0 2px 8px ${colors.secondary}4D` : 'none'
  }),

  // Messages section
  messagesContainer: {
    flex: 1,
    width: '100%',
    overflowY: 'auto',
    overflowX: 'hidden',
    marginTop: 'var(--messages-margin-top)',
    WebkitOverflowScrolling: 'touch',
    position: 'relative',
    zIndex: 1,
    paddingBottom: 'calc(var(--is-mobile) * 160px + (1 - var(--is-mobile)) * 120px)',
    paddingTop: 'var(--messages-top-padding)'
  } as CSSProperties,

  messagesStack: {
    padding: 'calc(var(--is-mobile) * 0.5rem + (1 - var(--is-mobile)) * 1.5rem)',
    position: 'relative',
    zIndex: 1
  } as CSSProperties,

  messageWrapper: (hasClip: boolean): CSSProperties => ({
    position: 'relative',
    zIndex: hasClip ? 50 : 10,
    marginBottom: hasClip ? '20px' : '0'
  }),

  // Input section
  inputArea: {
    position: 'fixed',
    bottom: 0,
    left: '50%',
    transform: 'translateX(-50%)',
    width: '100%',
    background: 'rgba(0,0,0,0.95)',
    display: 'flex',
    justifyContent: 'center',
    padding: 'calc(var(--is-mobile) * 0.5rem + (1 - var(--is-mobile)) * 1rem)',
    zIndex: 50,
    maxWidth: 'calc(var(--is-mobile) * 100% + (1 - var(--is-mobile)) * 1200px)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    borderTop: '1px solid rgba(255, 255, 255, 0.1)'
  } as CSSProperties,

  inputBox: {
    ...commonStyles.card,
    width: '100%',
    maxWidth: 'calc(var(--is-mobile) * 100% + (1 - var(--is-mobile)) * 800px)',
    padding: 'calc(var(--is-mobile) * 0.75rem + (1 - var(--is-mobile)) * 1rem)'
  } as CSSProperties,

  inputContainer: {
    position: 'relative',
    width: '100%',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '15px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    display: 'flex',
    alignItems: 'center',
    padding: '0 8px 0 0',
    minHeight: '48px',
    touchAction: 'auto',
    overscrollBehavior: 'contain',
    isolation: 'isolate',
    zIndex: 60,
    transform: 'translateZ(0)',
    willChange: 'transform'
  } as CSSProperties,

  // Share dialog styles
  shareDialog: {
    backgroundColor: `${colors.darkBlue}F2`,
    color: colors.text.light,
    border: `1px solid ${colors.border}`,
    boxShadow: `0 8px 24px ${colors.shadow}`,
    padding: '20px',
    minHeight: '120px',
    maxWidth: '320px',
    zIndex: 2000,
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderRadius: '12px',
    position: 'absolute' as const,
    opacity: 1
  } as CSSProperties,

  shareLinkBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    padding: '10px',
    borderRadius: '6px',
    wordBreak: 'break-all',
    fontSize: '13px',
    fontFamily: 'monospace',
    color: 'rgba(255, 255, 255, 0.9)'
  } as CSSProperties,

  shareActionButton: (isCopied: boolean): CSSProperties => ({
    flex: 1,
    height: '36px',
    borderRadius: '6px',
    backgroundColor: isCopied ? '#2e7d32' : colors.secondary,
    transition: commonStyles.animation.transition
  }),

  closeButton: {
    flex: 1,
    height: '36px',
    borderRadius: '6px',
    color: 'rgba(255, 255, 255, 0.7)'
  } as CSSProperties,

  shareTitle: {
    color: colors.text.light,
    fontSize: '1rem',
    fontWeight: 600
  } as CSSProperties,

  shareDescription: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: '0.875rem',
    lineHeight: 1.4
  } as CSSProperties,

  shareButtonInPopover: {
    marginTop: '0.5rem'
  } as CSSProperties,

  generateShareButton: {
    width: '100%',
    height: '40px',
    borderRadius: '6px',
    padding: '0 12px',
    backgroundColor: colors.secondary,
    transition: commonStyles.animation.transition,
    fontWeight: 600
  } as CSSProperties,

  shareActionsContainer: {
    display: 'flex',
    gap: '8px',
    marginTop: '0.5rem'
  } as CSSProperties,

  textMessageContent: (isAssistant: boolean): CSSProperties => ({
    ...commonStyles.text.body,
    whiteSpace: 'pre-wrap',
    color: isAssistant ? colors.text.dark : colors.text.light,
    fontFamily: fonts.family.mono
  }),

  // Contact button section
  contactSection: {
    display: 'flex',
    flex: '0 0 auto',
    justifyContent: 'flex-start',
    alignItems: 'center',
    height: '100%',
    padding: '0 1rem',
    marginRight: 'auto'
  } as CSSProperties,

  contactButtonContainer: {
    marginRight: 'calc(var(--is-mobile) * 0.5rem + (1 - var(--is-mobile)) * 0)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%'
  } as CSSProperties,

  contactButton: (isHovered: boolean): CSSProperties => ({
    backgroundColor: isHovered ? colors.primary : colors.secondary,
    color: colors.text.light,
    height: '50px',
    width: '50px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: 'auto 0',
    transition: commonStyles.animation.transition,
    cursor: 'pointer',
    boxShadow: `0 2px 8px ${colors.secondary}4D`
  }),

  contactDialog: {
    backgroundColor: `${colors.darkBlue}F2`,
    color: colors.text.light,
    border: `1px solid ${colors.border}`,
    boxShadow: `0 8px 24px ${colors.shadow}`,
    padding: '20px',
    minHeight: '120px',
    maxWidth: '320px',
    zIndex: 2000,
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderRadius: '12px',
    position: 'absolute' as const,
    opacity: 1
  } as CSSProperties,

  contactTitle: {
    color: colors.text.light,
    fontSize: '1rem',
    fontWeight: 600
  } as CSSProperties,

  contactDescription: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: '0.875rem',
    lineHeight: 1.4
  } as CSSProperties,

  donateButton: {
    width: '90%',
    height: '40px',
    borderRadius: '6px',
    padding: '0 12px',
    backgroundColor: colors.secondary,
    color: colors.text.light,
    fontSize: '0.95rem',
    fontWeight: 600,
    transition: 'all 0.2s ease-in-out',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    boxShadow: `0 2px 8px ${colors.shadow}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    '&:hover': {
      backgroundColor: colors.primary,
      transform: 'translateY(-1px)',
      boxShadow: `0 4px 12px ${colors.shadow}`
    }
  } as CSSProperties,
};

// Textarea specific styles
export const textareaCSS = `
  .chat-input {
    width: calc(100% - 60px) !important;
    min-height: 24px;
    max-height: 150px;
    background: transparent !important;
    border: none;
    outline: none;
    color: ${colors.text.light};
    font-size: var(--input-font-size);
    padding: 12px 15px;
    margin-right: 10px;
    resize: none;
    overflow-y: auto;
    overflow-x: hidden;
    display: block;
    line-height: 1.4;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    box-sizing: border-box;
    border-radius: 15px;
    -webkit-appearance: none;
    appearance: none;
    font-family: ${fonts.family.mono} !important;
    letter-spacing: 0.02em;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-y;
    overscroll-behavior: contain;
    position: relative;
    z-index: 60;
    transform: translateZ(0);
    will-change: transform;
    isolation: isolate;
  }

  .chat-input::placeholder {
    color: rgba(255, 255, 255, 0.5);
    font-size: var(--placeholder-font-size);
    font-family: ${fonts.family.mono} !important;
    letter-spacing: 0.02em;
  }

  .chat-input:focus {
    outline: none;
    border: none;
    background: transparent !important;
  }

  .mobile-input {
    font-size: 16px !important;
    padding: 10px 12px !important;
    -webkit-overflow-scrolling: touch !important;
    touch-action: pan-y !important;
    overscroll-behavior: contain !important;
    font-family: 'Roboto Mono', monospace !important;
    isolation: isolate !important;
    position: relative !important;
    z-index: 60 !important;
    transform: translateZ(0) !important;
    will-change: transform !important;
    overflow: auto !important;
    resize: none !important;
  }

  .loading-placeholder {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: rgba(0, 0, 0, 0.5);
    color: white;
    font-family: ${fonts.family.mono};
    z-index: 10;
  }

  .loading-placeholder span {
    font-size: 16px;
  }
`; 