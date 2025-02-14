import { useEffect, useRef, useState } from 'react';
import { Box, Paper } from '@mantine/core';

interface VideoPlayerProps {
  src: string;
  subtitleSrc?: string;  // URL to the SRT subtitle file
  autoplay?: boolean;
  onVideoEnd?: () => void;
  onVideoLoaded?: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  subtitleSrc,
  autoplay = true,
  onVideoEnd,
  onVideoLoaded,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vttUrl, setVttUrl] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState<string>('initial');

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
      console.log('Video data loaded:', {
        duration: video.duration,
        size: video.videoWidth * video.videoHeight * 3, // Rough size estimate
        codec: video.currentSrc
      });
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
        currentSrc: videoRef.current?.currentSrc
      }
    });

    // Get more specific error message
    let errorMessage = 'Unknown error';
    const videoError = e.target?.error;
    if (videoError) {
      switch (videoError.code) {
        case 1:
          errorMessage = 'Video loading aborted';
          break;
        case 2:
          errorMessage = 'Network error while loading video';
          break;
        case 3:
          errorMessage = 'Video decoding failed';
          break;
        case 4:
          errorMessage = 'Video not supported';
          break;
      }
      errorMessage += `: ${videoError.message}`;
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
    console.log('VideoPlayer props:', { src, subtitleSrc, loadingState });
    
    // Reset states when src changes
    setError(null);
    setLoadingState('initial');
    
    if (videoRef.current && autoplay && !hasPlayed) {
      videoRef.current.play().catch((error) => {
        console.error('Video playback error:', error);
        setError(error.message);
      });
      setHasPlayed(true);
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
  }, [src, autoplay, hasPlayed]);

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
            vttContent += `${start} --> ${end}\n${text}\n\n`;
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
    <Paper shadow="sm" radius="md" withBorder style={{ background: '#0d1b2a' }}>
      <Box style={{ position: 'relative', width: '100%', paddingTop: '56.25%' }}>
        <video
          ref={videoRef}
          controls
          crossOrigin="anonymous"
          preload="metadata"
          onError={handleError}
          onLoadStart={handleLoadStart}
          onCanPlay={handleCanPlay}
          onLoadedData={handleLoadedData}
          onLoadedMetadata={handleMetadataLoaded}
          onEnded={onVideoEnd}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            borderRadius: 'inherit'
          }}
          playsInline  // Better mobile support
        >
          <source 
            src={src} 
            type="video/mp4"
            onError={(e) => console.error('Source error:', e)} 
          />
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
          <Box
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: '#ff4444',
              background: 'rgba(13, 27, 42, 0.9)',
              padding: '1rem',
              borderRadius: '4px',
              textAlign: 'center'
            }}
          >
            Error: {error}
          </Box>
        )}
      </Box>
    </Paper>
  );
}; 