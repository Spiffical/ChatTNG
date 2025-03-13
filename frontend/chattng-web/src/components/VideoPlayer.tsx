import { useEffect, useRef, useState } from 'react';
import { Box, Paper, ActionIcon } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { getStyles } from '../styles/VideoPlayerStyles';
import { IconPlayerPlay } from '@tabler/icons-react';

// Helper function to detect iOS
const isIOS = () => {
  if (typeof window === 'undefined') return false;
  
  // Get all the possible indicators of iOS
  const userAgent = navigator.userAgent;
  const platform = navigator.platform;
  const maxTouchPoints = navigator.maxTouchPoints || 0;
  
  // Log detection details for debugging
  console.log('Device detection:', {
    userAgent,
    platform,
    maxTouchPoints,
    isStandardIOS: /iPad|iPhone|iPod/.test(userAgent),
    isMacWithTouch: platform === 'MacIntel' && maxTouchPoints > 1,
    isSafari: /Safari/.test(userAgent) && !/Chrome/.test(userAgent),
    timestamp: new Date().toISOString()
  });
  
  // Check for standard iOS devices
  const isStandardIOS = /iPad|iPhone|iPod/.test(userAgent);
  
  // Check for iPad OS which reports as MacIntel but has touch support
  const isMacWithTouch = platform === 'MacIntel' && maxTouchPoints > 1;
  
  // Some iOS Safari browsers use a different user agent pattern
  const isSafariMobile = /Safari/.test(userAgent) && 
                         (/Mobile/.test(userAgent) || /Apple/.test(userAgent)) && 
                         !/Chrome/.test(userAgent);
  
  const isIOS = isStandardIOS || isMacWithTouch || (isSafariMobile && (platform === 'MacIntel' || platform === 'iPhone' || platform === 'iPad' || platform === 'iPod'));
  
  console.log(`iOS detection result: ${isIOS}`);
  return isIOS;
};

// Helper function to detect Firefox
const isFirefox = () => {
  if (typeof window === 'undefined') return false;
  const ua = navigator.userAgent.toLowerCase();
  return ua.includes('firefox') || ua.includes('fennec');
};

interface VideoPlayerProps {
  src: string;
  subtitleSrc?: string;  // URL to the SRT subtitle file
  autoplay?: boolean;
  onVideoEnd?: () => void;
  onVideoLoaded?: () => void;
}

// Helper function to get transcoded video URL
const getTranscodedUrl = async (originalUrl: string, forceTranscode = false): Promise<string> => {
  const isIOSDevice = isIOS();
  console.log('Video transcoding request:', {
    originalUrl,
    isIOSDevice,
    forceTranscode,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    touchPoints: navigator.maxTouchPoints,
    timestamp: new Date().toISOString()
  });

  // If not iOS and not forcing transcoding, just return the original URL
  if (!isIOSDevice && !forceTranscode) {
    console.log('Non-iOS device detected, using original URL');
    return originalUrl;
  }

  try {
    // Get the API base URL from environment
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    // Build the transcoding URL with proper encoding
    let transcodeUrl = `${apiBaseUrl}/api/video/transcode?url=${encodeURIComponent(originalUrl)}`;
    if (forceTranscode) {
      transcodeUrl += '&force=true';
    }
    
    // Call our transcoding endpoint
    console.log(`Calling transcoding endpoint: ${transcodeUrl}`);
    const response = await fetch(transcodeUrl, {
      // Don't auto-follow redirects so we can handle them explicitly
      redirect: 'manual'
    });
    
    console.log('Transcoding response:', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      isRedirect: response.redirected,
      url: response.url
    });

    // If we got a redirect (307), use the redirect URL
    if (response.status === 307 && response.headers.has('location')) {
      const redirectUrl = response.headers.get('location');
      console.log(`Received redirect to: ${redirectUrl}`);
      return redirectUrl || originalUrl;
    }
    
    // For streaming response (200), use the transcoding endpoint URL
    if (response.status === 200) {
      console.log('Using transcoded streaming URL');
      return response.url;
    }

    // Fallback to original URL if something went wrong
    console.log('Unexpected response, falling back to original URL');
    return originalUrl;
  } catch (err) {
    console.error('Error getting transcoded URL:', {
      error: err,
      message: err instanceof Error ? err.message : String(err),
      stack: err instanceof Error ? err.stack : undefined
    });
    return originalUrl; // Fallback to original URL
  }
};

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  subtitleSrc,
  autoplay = true,
  onVideoEnd,
  onVideoLoaded,
}) => {
  const isMobile = useMediaQuery('(max-width: 768px)') ?? false;
  const styles = getStyles(isMobile);
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [videoSrc, setVideoSrc] = useState(src);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vttUrl, setVttUrl] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState<string>('initial');
  const [showPlayButton, setShowPlayButton] = useState(false);
  const isIOSDevice = isIOS();
  const isFirefoxBrowser = isFirefox();
  const [touchStartY, setTouchStartY] = useState<number | null>(null);
  const [touchStartTime, setTouchStartTime] = useState<number | null>(null);

  // Get transcoded URL for iOS devices
  useEffect(() => {
    console.log('VideoPlayer props:', { src, subtitleSrc, loadingState });
    
    // Reset states when src changes
    setError(null);
    setLoadingState('initial');
    setShowPlayButton(false); // Never show custom play button on iOS
    
    // Get transcoded URL for iOS devices
    const setupVideoSource = async () => {
      setLoadingState('fetching');
      try {
        // Check URL parameters for force_transcode=true
        const urlParams = new URLSearchParams(window.location.search);
        const forceTranscode = urlParams.get('force_transcode') === 'true';
        
        // For iOS devices or if force_transcode is enabled, get the transcoded URL with AAC audio
        if (isIOSDevice || forceTranscode) {
          console.log(`${isIOSDevice ? 'iOS device' : 'Force transcode'} detected, getting transcoded URL`);
          const transcodedUrl = await getTranscodedUrl(src, forceTranscode);
          console.log('Transcoded URL result:', transcodedUrl);
          setVideoSrc(transcodedUrl);
        } else {
          // For non-iOS devices, use the original source
          setVideoSrc(src);
        }
        setLoadingState('loaded');
      } catch (err) {
        console.error('Error setting up video source:', err);
        setLoadingState('error');
        setError('Failed to prepare video for playback');
        // Fallback to original source
        setVideoSrc(src);
      }
    };
    
    setupVideoSource();

    if (videoRef.current) {
      // Set crossOrigin attribute for CORS
      videoRef.current.crossOrigin = "anonymous";
      
      if (autoplay && !hasPlayed && !isIOSDevice) {
        // Only autoplay on non-iOS devices
        dismissKeyboard();
        setHasPlayed(true);
      }
    }

    // Validate video URL with proper CORS headers
    const validateVideo = async () => {
      try {
        const response = await fetch(src, { 
          method: 'HEAD',
          mode: 'cors',
          credentials: 'omit',
          headers: {
            'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.8'
          }
        });
        
        if (!response.ok) {
          console.error('Video validation failed:', {
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries()),
            url: src
          });
          setError(`Video load failed: ${response.status} ${response.statusText}`);
        } else {
          console.log('Video validation succeeded:', {
            contentType: response.headers.get('content-type'),
            contentLength: response.headers.get('content-length'),
            cors: response.headers.get('access-control-allow-origin')
          });
        }
      } catch (err: any) {
        console.error('Video fetch error:', err);
        if (err.message.includes('CORS')) {
          setError('Video access blocked by CORS policy. Please check server configuration.');
        } else {
          setError(`Video fetch error: ${err.message}`);
        }
      }
    };
    validateVideo();
  }, [src, autoplay, hasPlayed, isIOSDevice]);

  // Handle video metadata loaded - ensure subtitles are showing
  const handleMetadataLoaded = () => {
    const video = videoRef.current;
    if (video) {
      console.log('Video metadata loaded:', {
        duration: video.duration,
        videoWidth: video.videoWidth,
        videoHeight: video.videoHeight,
        readyState: video.readyState,
        networkState: video.networkState,
        error: video.error
      });
      
      if (video.duration === 0 || video.videoWidth === 0 || video.videoHeight === 0) {
        setError('Invalid video dimensions or duration');
        return;
      }

      if (video.textTracks.length > 0) {
        Array.from(video.textTracks).forEach(track => {
          track.mode = 'showing';
        });
      }
    }
    setLoadingState('metadata-loaded');
    if (onVideoLoaded) onVideoLoaded();
    
    // Dispatch a custom event that the video has loaded
    document.dispatchEvent(new CustomEvent('videoLoaded'));
  };

  // Handle touch start event
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartY(e.touches[0].clientY);
    setTouchStartTime(Date.now());
  };

  // Handle touch end event
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartY === null || touchStartTime === null) return;
    
    const touchEndY = e.changedTouches[0].clientY;
    const touchEndTime = Date.now();
    
    // Calculate vertical distance and time of touch
    const verticalDistance = Math.abs(touchEndY - touchStartY);
    const touchDuration = touchEndTime - touchStartTime;
    
    // If the touch was a quick tap (less than 200ms) and didn't move much vertically (less than 10px),
    // treat it as a legitimate video interaction
    if (touchDuration < 200 && verticalDistance < 10) {
      handleVideoInteraction(e);
    }
    
    // Reset touch tracking
    setTouchStartY(null);
    setTouchStartTime(null);
  };

  // Simplified video interaction handler
  const handleVideoInteraction = (e: React.MouseEvent | React.TouchEvent) => {
    console.log('Video interaction detected:', {
      type: e.type,
      timestamp: new Date().toISOString()
    });

    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    
    e.stopPropagation();
    
    const video = videoRef.current;
    if (!video || !video.paused) return;
    
    video.play().catch(err => console.error('Error playing video:', err));
  };

  // This function is used in the video's onClick and onPlay handlers
  const dismissKeyboard = () => {
    // Blur any active input elements to hide the keyboard
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    
    // Play the video if it's not already playing
    if (videoRef.current && videoRef.current.paused) {
      videoRef.current.play().catch(error => {
        console.error('Video play error:', error);
      });
    }
  };

  // Handle video end event
  const handleVideoEnd = () => {
    console.log('Video playback ended');
    // Ensure we call onVideoEnd synchronously
    onVideoEnd?.();
  };

  const handleLoadStart = () => {
    console.log('Video load started');
    setLoadingState('loading');
  };

  const handleCanPlay = () => {
    console.log('Video can play');
    setLoadingState('ready');
  };

  const handleLoadedData = () => {
    const video = videoRef.current;
    if (video) {
      // Get audio tracks info if available
      let audioInfo: string | {
        count: number;
        tracks: Array<{
          enabled: boolean;
          kind: string;
          label: string;
          language: string;
          id: string;
        }>;
      } = 'Not available';
      
      try {
        if ('audioTracks' in video) {
          const audioTracks = (video as any).audioTracks;
          audioInfo = {
            count: audioTracks.length,
            tracks: Array.from(audioTracks).map((track: any) => ({
              enabled: track.enabled,
              kind: track.kind,
              label: track.label,
              language: track.language,
              id: track.id
            }))
          };
        }
      } catch (err) {
        console.error('Error getting audio tracks:', err);
      }

      console.log('Video data loaded:', {
        duration: video.duration,
        size: video.videoWidth * video.videoHeight * 3,
        codec: video.currentSrc,
        audioInfo,
        mediaError: video.error,
        networkState: video.networkState,
        readyState: video.readyState
      });

      // On iOS, try to detect audio format
      if (isIOSDevice) {
        console.log('iOS device detected, checking media capabilities...');
        try {
          const mediaSource = window.MediaSource || (window as any).WebKitMediaSource;
          if (mediaSource) {
            console.log('Supported MIME types:', {
              mp4aac: MediaSource.isTypeSupported('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
              mp4mp3: MediaSource.isTypeSupported('video/mp4; codecs="avc1.42E01E, mp3"'),
              webmaac: MediaSource.isTypeSupported('video/webm; codecs="vp8, vorbis"')
            });
          }
        } catch (err) {
          console.error('Error checking media capabilities:', err);
        }
      }
    }
  };

  const handleError = (e: any) => {
    console.error('Video error:', {
      error: e,
      videoElement: {
        readyState: videoRef.current?.readyState,
        networkState: videoRef.current?.networkState,
        error: videoRef.current?.error,
        crossOrigin: videoRef.current?.crossOrigin,
        currentSrc: videoRef.current?.currentSrc,
        muted: videoRef.current?.muted,
        paused: videoRef.current?.paused,
        hasAudio: Boolean((videoRef.current as any)?.mozHasAudio) || Boolean((videoRef.current as any)?.webkitAudioDecodedByteCount)
      },
      sourceURL: {
        original: src,
        current: videoSrc,
        isDifferent: src !== videoSrc
      },
      isIOS: isIOSDevice
    });

    // Media error codes: https://developer.mozilla.org/en-US/docs/Web/API/MediaError/code
    let errorMessage = 'Error playing video.';
    const mediaError = videoRef.current?.error;
    
    if (mediaError) {
      switch(mediaError.code) {
        case MediaError.MEDIA_ERR_ABORTED:
          errorMessage = 'Video playback aborted by user.';
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          errorMessage = 'Network error while loading video.';
          break;
        case MediaError.MEDIA_ERR_DECODE:
          if (isIOSDevice) {
            errorMessage = 'Video format or codec not supported by iOS. This might be an audio codec issue.';
            console.warn('iOS decode error - this often happens with non-AAC audio codecs', {
              src: videoSrc,
              originalSrc: src,
              isTranscoded: videoSrc !== src
            });
            
            // If we're using the original URL (not transcoded) or transcoding failed, try again with force option
            if ((videoSrc === src || mediaError.message?.includes('audio')) && isIOSDevice) {
              console.log('Attempting to force transcoding after decode error');
              getTranscodedUrl(src, true)
                .then(url => {
                  if (url !== videoSrc) {
                    console.log('Switching to forced transcoded URL after decode error');
                    setVideoSrc(url);
                    setError('Trying with transcoded audio...');
                    
                    // Give some time for the error message to show before clearing it
                    setTimeout(() => {
                      if (videoRef.current && !videoRef.current.error) {
                        setError(null); // Clear error if video successfully loaded
                      }
                    }, 3000);
                  }
                })
                .catch(err => {
                  console.error('Failed to get transcoded URL after decode error:', err);
                  errorMessage = 'Failed to transcode audio for iOS playback.';
                });
            }
          } else {
            errorMessage = 'Video decode error. The video might be corrupted or use an unsupported format.';
          }
          break;
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMessage = 'Video format not supported.';
          break;
        default:
          errorMessage = `Video error (${mediaError.code}): ${mediaError.message}`;
      }
    }

    // Check if it's a CORS error
    if (e.target?.error?.message?.includes('CORS') || 
        (e instanceof Error && e.message.includes('CORS'))) {
      errorMessage = 'Video access blocked by CORS policy. Please check server configuration.';
      console.error('CORS error details:', {
        src: src,
        crossOrigin: videoRef.current?.crossOrigin,
        headers: e.target?.error?.headers
      });
    }

    setError(errorMessage);
  };

  useEffect(() => {
    // Convert SRT to VTT when subtitle source changes
    const convertSrtToVtt = async () => {
      if (!subtitleSrc) {
        setVttUrl(null);
        return;
      }

      try {
        console.log('Fetching subtitles from:', subtitleSrc);
        const response = await fetch(subtitleSrc);
        if (!response.ok) {
          throw new Error(`Failed to fetch subtitles: ${response.statusText}`);
        }

        const srtContent = await response.text();
        console.log('Received SRT content:', srtContent.substring(0, 200) + '...');
        
        // Convert SRT to VTT
        let vttContent = 'WEBVTT\n\n';
        const srtBlocks = srtContent.trim().split('\n\n');
        
        for (const block of srtBlocks) {
          const lines = block.split('\n');
          if (lines.length >= 3) {
            // Skip the subtitle number
            const timecode = lines[1]
              .replace(/,/g, '.') // Replace ALL commas with periods for milliseconds
              .replace(/ --> /g, ' --> '); // Ensure proper arrow format
            
            // Ensure proper formatting of timestamps (HH:MM:SS.mmm)
            const [start, end] = timecode.split(' --> ').map(time => {
              if (!time.includes('.')) return time + '.000';
              return time;
            });
            
            const text = lines.slice(2).join('\n');
            // Add position information to force subtitle to bottom
            vttContent += `${start} --> ${end} line:90% position:50% align:center\n${text}\n\n`;
          }
        }

        console.log('Generated VTT content:', vttContent.substring(0, 200) + '...');

        // Create blob URL for the VTT content
        const blob = new Blob([vttContent], { type: 'text/vtt' });
        const url = URL.createObjectURL(blob);
        setVttUrl(url);
        console.log('Created VTT URL:', url);

        // Force refresh of video track list
        if (videoRef.current) {
          const video = videoRef.current;
          // Small delay to ensure track is added
          setTimeout(() => {
            if (video.textTracks.length > 0) {
              Array.from(video.textTracks).forEach(track => {
                track.mode = 'showing';
                console.log('Set track mode to showing after conversion');
              });
            }
          }, 100);
        }
      } catch (err) {
        console.error('Error converting subtitles:', err);
        setError('Failed to load subtitles');
      }
    };

    convertSrtToVtt();

    // Cleanup blob URL on unmount or when subtitle source changes
    return () => {
      if (vttUrl) {
        URL.revokeObjectURL(vttUrl);
      }
    };
  }, [subtitleSrc]);

  const handleTrackLoad = () => {
    console.log('Subtitle track loaded');
    // Ensure track is showing when loaded
    const video = videoRef.current;
    if (video && video.textTracks.length > 0) {
      Array.from(video.textTracks).forEach(track => {
        track.mode = 'showing';
        console.log('Set track mode to showing on track load');
      });
    }
  };

  return (
    <Paper
      shadow="sm"
      radius="md"
      withBorder
      style={styles.container}
      ref={containerRef}
      onClick={handleVideoInteraction}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <style>
        {`
          video::cue {
            font-size: clamp(14px, 4vw, 20px);
            line-height: 1.4;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
          }
        `}
      </style>
      <Box style={styles.videoWrapper}>
        {showPlayButton && !isIOSDevice && (
          <ActionIcon
            variant="filled"
            radius="xl"
            size="xl"
            onClick={handleVideoInteraction}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 1000,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
              },
            }}
          >
            <IconPlayerPlay size={32} />
          </ActionIcon>
        )}
        {loadingState === 'transcoding' && (
          <Box style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1000,
            textAlign: 'center',
            color: 'white',
          }}>
            Preparing video...
          </Box>
        )}
        <video
          ref={videoRef}
          style={styles.video}
          autoPlay={!isIOSDevice && autoplay}
          playsInline
          controls
          onContextMenu={(e) => e.preventDefault()}
          crossOrigin="anonymous"
          preload="auto"
          {...(isFirefoxBrowser ? {} : { controlsList: "nodownload nofullscreen" })}
          onLoadedData={handleLoadedData}
          onLoadedMetadata={handleMetadataLoaded}
          onEnded={handleVideoEnd}
          onError={handleError}
          onPlay={dismissKeyboard}
          onClick={handleVideoInteraction}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          onLoadStart={handleLoadStart}
          onWaiting={() => setLoadingState('buffering')}
          onCanPlay={handleCanPlay}
          {...(!isFirefoxBrowser && { 
            "x-webkit-airplay": "allow", 
            "x-webkit-playsinline": true, 
            "webkit-playsinline": true 
          })}
        >
          <source src={videoSrc} type="video/mp4" />
          {vttUrl && (
            <track
              kind="subtitles"
              src={vttUrl}
              srcLang="en"
              label="English"
              default
              onLoad={handleTrackLoad}
            />
          )}
          Your browser does not support HTML5 video.
        </video>
        {error && (
          <Box style={styles.errorMessage}>Error: {error}</Box>
        )}
      </Box>
    </Paper>
  );
}; 