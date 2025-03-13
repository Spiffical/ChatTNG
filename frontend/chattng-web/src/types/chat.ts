// Message types
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  isPending?: boolean;
  clip_url?: string;
  subtitle_url?: string;
  clip_metadata?: ClipMetadata;
}

export interface ClipMetadata {
  clip_path: string;
  start_time: number;
  end_time: number;
  character?: string;
  episode?: string;
  season?: number;
  confidence?: number;
}

// Window augmentation for global types
declare global {
  interface Window {
    webkitAudioContext: typeof AudioContext;
    __NEXT_DATA__?: {
      props?: {
        pageProps?: {
          apiUrl?: string;
        };
      };
    };
  }
} 